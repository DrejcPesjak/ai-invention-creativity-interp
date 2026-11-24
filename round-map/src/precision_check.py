"""Diagnostic: is the next-token distribution stable across batch shapes? usage: precision_check.py <bf16off|8bit|4bit|4bit32>
Writes results/precision_check_<mode>.json. Contexts: the 8 hesitation points of the first (8-bit) stage D greedy path."""
import sys, json, time, os, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen, tools
from transformers import AutoModelForCausalLM, BitsAndBytesConfig
mode = sys.argv[1]
ctx = json.load(open(os.path.join(tools.ROOT, "results", "precision_check_contexts.json")))
if mode in ("8bit", "4bit"):
    lm = gen.LM(gen.TUNED, mode)
else:
    lm = gen.LM.__new__(gen.LM)
    from transformers import AutoTokenizer
    lm.tok = AutoTokenizer.from_pretrained(gen.TUNED); lm.tok.padding_side = "left"
    if mode == "bf16off":
        lm.model = AutoModelForCausalLM.from_pretrained(gen.TUNED, dtype=torch.bfloat16, device_map="auto",
                                                        max_memory={0: "4GiB", "cpu": "10GiB"})
    else:
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float32)
        lm.model = AutoModelForCausalLM.from_pretrained(gen.TUNED, quantization_config=q, device_map={"": 0},
                                                        dtype=torch.float32)
    lm.model.eval()
    lm.eos = [lm.tok.convert_tokens_to_ids("<|im_end|>"), lm.tok.convert_tokens_to_ids("<|endoftext|>")]
ids = [15454, 17961, 421, 11994, 7177, 5611, 1958, 501]  # a few token ids to follow
def probs(res):
    return [[round(float(r["full"][t]), 4) for t in ids] + [r["top"][0][0], round(r["top"][0][1], 4)] for r in res]
out = dict(mode=mode, vram=torch.cuda.memory_allocated() / 2**30)
t = time.time()
out["single"] = probs([lm.next_probs([s], k=3)[0] for s in ctx])
out["single_s"] = time.time() - t
out["padded"] = probs(lm.next_probs(ctx, k=3))
out["dup4"] = probs([lm.next_probs([s] * 4, k=3)[2] for s in ctx])
def maxdiff(a, b):
    return max(abs(x - y) for ra, rb in zip(a, b) for x, y in zip(ra[:-2], rb[:-2]))
out["maxdiff_single_vs_padded"] = maxdiff(out["single"], out["padded"])
out["maxdiff_single_vs_dup4"] = maxdiff(out["single"], out["dup4"])
if mode != "bf16off":
    torch.manual_seed(0); t = time.time()
    o = lm.generate([ctx[0][:-3]] * 8, max_new_tokens=700)
    out["batch8_s"] = time.time() - t; out["batch8_steps"] = max(x["n_new"] for x in o)
    out["peak"] = torch.cuda.max_memory_allocated() / 2**30
json.dump(out, open(os.path.join(tools.ROOT, "results", f"precision_check_{mode}.json"), "w"), indent=1)
print(mode, {k: v for k, v in out.items() if k not in ("single", "padded", "dup4")})
print("top1 single:", [r[-2:] for r in out["single"]])
