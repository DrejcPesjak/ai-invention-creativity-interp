"""Stage 0: pick a precision (bf16 -> 8bit -> 4bit), then 10 answers to SPEC alone. Stop gate.
usage: python src/stage0.py [precision ...]     (default: try all three in order)
"""
import json, os, sys, time, traceback
import torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools, gen

SEED = 1000
order = sys.argv[1:] or ["bf16", "bf16off", "8bit", "4bit"]
msgs = [{"role": "user", "content": open(os.path.join(tools.ROOT, "prompts", "A_unprompted.txt")).read().strip()}]
report = {"tried": []}
lm = None
for prec in order:
    entry = {"precision": prec}
    try:
        t0 = time.time()
        lm = gen.LM(gen.TUNED, prec)
        entry["load_s"] = round(time.time() - t0, 1)
        entry["vram_after_load_gb"] = round(torch.cuda.memory_allocated() / 2**30, 2)
        pid = lm.prompt_ids(msgs)
        if prec == order[0]:
            print("PROMPT TAIL:", repr(lm.tok.decode(pid[-30:])))
        torch.manual_seed(SEED)
        t0 = time.time()
        outs = lm.generate([pid] * 8, max_new_tokens=700)
        dt = time.time() - t0
        ntok = max(o["n_new"] for o in outs)
        entry.update(batch8_s=round(dt, 1), steps=ntok, steps_per_s=round(ntok / dt, 1),
                     vram_peak_gb=round(torch.cuda.max_memory_allocated() / 2**30, 2))
        # plan gate: "slower than about 2 minutes per batch of 8" on this task's real answers
        entry["usable"] = dt < 130
        print(entry, flush=True)
        report["tried"].append(entry)
        if entry["usable"]:
            report["precision"] = prec
            break
        lm.unload(); lm = None
    except Exception as e:
        entry["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        traceback.print_exc()
        print(entry, flush=True)
        report["tried"].append(entry)
        try:
            lm.unload()
        except Exception:
            pass
        lm = None
        import gc; gc.collect(); torch.cuda.empty_cache()

if "precision" not in report:
    json.dump(report, open(os.path.join(tools.ROOT, "results", "stage0_report.json"), "w"), indent=1)
    sys.exit("no usable precision")
report.update(model=gen.TUNED, base=gen.BASE, seed=SEED, gpu_budget=gen.GPU_BUDGET)
json.dump(report, open(gen.CFG_PATH, "w"), indent=1)

out = os.path.join(tools.ROOT, "results", "stage0.jsonl")
jobs = [dict(id=f"S0-{i}", stage="0", messages=msgs) for i in range(10)]
t0 = time.time()
gen.run_jobs(lm, jobs, out, batch=10, seed=SEED)
rows = [json.loads(l) for l in open(out)]
report["n_pass_core46"] = sum(r["pass_all"] for r in rows)
report["n_pass_strict48"] = sum(r["strict_all"] for r in rows)
report["gen_s_for_10"] = round(time.time() - t0, 1)
report["vram_peak_gb"] = round(torch.cuda.max_memory_allocated() / 2**30, 2)
report["gate_passed_core46"] = report["n_pass_core46"] >= 5
report["gate_passed_strict48"] = report["n_pass_strict48"] >= 5
json.dump(report, open(os.path.join(tools.ROOT, "results", "stage0_report.json"), "w"), indent=1)
print(json.dumps(report, indent=1))
for r in rows:
    print(r["id"], r["n_passed"], r["sig"], r["n_new"], r["fails"][:2])
