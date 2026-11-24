"""generate: the one model wrapper used by every stage. One model in memory at a time."""
import gc, json, os, sys, time
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, LogitsProcessorList

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools

TUNED = "Qwen/Qwen3-4B"
BASE = "Qwen/Qwen3-4B-Base"
GPU_BUDGET = "5800MiB"
CFG_PATH = os.path.join(tools.ROOT, "results", "model_config.json")


def chosen_precision():
    return json.load(open(CFG_PATH))["precision"]


class LM:
    def __init__(self, model_id=TUNED, precision=None):
        precision = precision or chosen_precision()
        self.model_id, self.precision = model_id, precision
        # the tokenizer (and chat template) always comes from the tuned model: both models get the same ids
        self.tok = AutoTokenizer.from_pretrained(TUNED)
        self.tok.padding_side = "left"
        if self.tok.pad_token_id is None:
            self.tok.pad_token = self.tok.eos_token
        kw = {}
        if precision == "bf16":
            kw = dict(dtype=torch.bfloat16, device_map={"": 0})
        elif precision == "bf16off":
            # true bf16 weights; the layers that do not fit on the 8 GB card run on the CPU
            kw = dict(dtype=torch.bfloat16, device_map="auto", max_memory={0: GPU_BUDGET, "cpu": "10GiB"})
        else:
            from transformers import BitsAndBytesConfig
            if precision == "8bit":
                q = BitsAndBytesConfig(load_in_8bit=True)
            elif precision == "4bit":
                q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                       bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=False)
            else:
                raise ValueError(precision)
            kw = dict(quantization_config=q, device_map={"": 0},
                      dtype=torch.float16 if precision == "8bit" else torch.bfloat16)
        self.model = AutoModelForCausalLM.from_pretrained(model_id, **kw)
        self.model.eval()
        self.eos = [self.tok.convert_tokens_to_ids("<|im_end|>"), self.tok.convert_tokens_to_ids("<|endoftext|>")]

    def unload(self):
        del self.model
        gc.collect()
        torch.cuda.empty_cache()

    def prompt_ids(self, messages):
        """messages -> token ids, ending with the assistant header (thinking disabled)."""
        text = self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                            enable_thinking=False)
        return self.tok(text, add_special_tokens=False)["input_ids"]

    def _pad(self, seqs):
        m = max(len(s) for s in seqs)
        pad = self.tok.pad_token_id
        ids = torch.tensor([[pad] * (m - len(s)) + s for s in seqs], device="cuda")
        att = torch.tensor([[0] * (m - len(s)) + [1] * len(s) for s in seqs], device="cuda")
        return ids, att

    @torch.no_grad()
    def generate(self, prompts, forced=None, max_new_tokens=700, sample=True, temperature=1.0, top_p=0.95,
                 want_probs=False, topk_keep=5):
        """prompts: list of token-id lists. forced: optional list of token-id lists (forced beginning of the answer).
        Returns list of dict(text, ids[, steps]) where text/ids include the forced beginning.
        steps (want_probs): per generated token: chosen id, its probability (T=1, no top-p), and top-k (id, prob)."""
        forced = forced or [[] for _ in prompts]
        seqs = [p + f for p, f in zip(prompts, forced)]
        ids, att = self._pad(seqs)
        kw = dict(max_new_tokens=max_new_tokens, eos_token_id=self.eos, pad_token_id=self.tok.pad_token_id)
        if sample:
            kw.update(do_sample=True, temperature=temperature, top_p=top_p, top_k=None)
        else:
            kw.update(do_sample=False, temperature=None, top_p=None, top_k=None)
        rec = []
        if want_probs:
            assert not sample, "per-step probabilities are recorded for greedy decoding only"

            def record(input_ids, scores):  # raw logits (no warpers in greedy mode)
                p = torch.softmax(scores.float(), -1)
                tp, ti = p.topk(topk_keep, -1)
                rec.append((ti.tolist(), tp.tolist()))
                return scores
            kw.update(logits_processor=LogitsProcessorList([record]))
        out = self.model.generate(input_ids=ids, attention_mask=att, **kw)
        new = out[:, ids.shape[1]:].tolist()
        res = []
        for b in range(len(prompts)):
            toks = []
            for t in new[b]:
                if t in self.eos:
                    break
                toks.append(t)
            full = forced[b] + toks
            d = dict(text=self.tok.decode(full, skip_special_tokens=True), ids=full, n_new=len(toks),
                     hit_limit=(len(toks) == max_new_tokens))
            if want_probs:
                steps = []
                for s in range(len(toks)):
                    ti, tp = rec[s][0][b], rec[s][1][b]
                    assert ti[0] == toks[s], "greedy token is not the recorded top-1"
                    steps.append(dict(id=toks[s], p=tp[0], top=[[i, x] for i, x in zip(ti, tp)]))
                d["steps"] = steps
            res.append(d)
        return res

    @torch.no_grad()
    def next_probs(self, seqs, k=20):
        """For each token-id list: the next-token distribution's top-k [(id, prob)], plus a lookup function result."""
        ids, att = self._pad(seqs)
        h = self.model.model(input_ids=ids, attention_mask=att).last_hidden_state[:, -1:]
        logits = self.model.lm_head(h)[:, 0].float()  # last position only (full-sequence logits do not fit)
        p = torch.softmax(logits, -1)
        tp, ti = p.topk(k, -1)
        return [dict(top=[[int(i), float(x)] for i, x in zip(ti[b], tp[b])], full=p[b].cpu()) for b in range(len(seqs))]


def safe_generate(lm, prompts, forced=None, **kw):
    """generate; on CUDA out-of-memory split the batch in half and retry (outside the except block,
    otherwise the traceback keeps the failed batch's tensors alive)."""
    oom = False
    try:
        return lm.generate(prompts, forced=forced, **kw)
    except torch.OutOfMemoryError:
        oom = True
    if oom:
        gc.collect(); torch.cuda.empty_cache()
        if len(prompts) == 1:
            raise RuntimeError("out of memory with a batch of 1")
        h = len(prompts) // 2
        print(f"  OOM at batch {len(prompts)}: splitting", flush=True)
        f1, f2 = (forced[:h], forced[h:]) if forced else (None, None)
        return safe_generate(lm, prompts[:h], f1, **kw) + safe_generate(lm, prompts[h:], f2, **kw)


def run_jobs(lm, jobs, out_path, batch=12, seed=0, max_new_tokens=700, evaluate=True, log=print):
    """jobs: list of dict(id=..., messages=[...], **meta). Appends one row per job to out_path (resumable by id)."""
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path):
            done.add(json.loads(line)["id"])
    todo = [j for j in jobs if j["id"] not in done]
    log(f"{out_path}: {len(done)} done, {len(todo)} to do")
    # keep similar prompt lengths together
    for j in todo:
        j["_pids"] = lm.prompt_ids(j["messages"])
    todo.sort(key=lambda j: len(j["_pids"]))
    torch.manual_seed(seed + len(done))
    t00 = time.time()
    for b0 in range(0, len(todo), batch):
        chunk = todo[b0:b0 + batch]
        t0 = time.time()
        outs = safe_generate(lm, [j["_pids"] for j in chunk], max_new_tokens=max_new_tokens)
        dt = time.time() - t0
        with open(out_path, "a") as f:
            for j, o in zip(chunk, outs):
                row = {k: v for k, v in j.items() if k != "_pids"}
                row.update(text=o["text"], n_new=o["n_new"], hit_limit=o["hit_limit"])
                if evaluate:
                    row.update(tools.evaluate(o["text"]))
                f.write(json.dumps(row) + "\n")
        log(f"  batch {b0 // batch + 1}/{(len(todo) + batch - 1) // batch} {dt:.0f}s "
            f"(total {time.time() - t00:.0f}s) max_new={max(o['n_new'] for o in outs)}")
