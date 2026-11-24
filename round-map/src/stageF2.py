"""Stage F2: scoring loop. Score = average grid-cell reads over the 48 tests (lower is better).
usage: python src/stageF2.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch
import tools

SEED, ROUNDS, PER_ROUND = 1007, 8, 8
OUT = os.path.join(tools.ROOT, "results", "stageF2.jsonl")
STATE = os.path.join(tools.ROOT, "results", "stageF2_rounds.json")
SCORE_NOTE = ("Scoring: each time the code reads a cell of grid (indexing a row or iterating over it) counts as one "
              "read. The score of a solution is its average number of reads over the tests; lower is better.")
ASK = "Write a different solve that passes the same tests and reads fewer cells."
TEMPLATE = "{SPEC}\n\n" + SCORE_NOTE + "\n\nThe current best solutions:\n\n{TOP}\n\n" + ASK


def render(top):
    parts = []
    for i, t in enumerate(top, 1):
        parts.append(f"Solution {i} (score {t['reads']:.1f}):\n```python\n{t['code']}\n```")
    return TEMPLATE.replace("{SPEC}", tools.SPEC).replace("{TOP}", "\n\n".join(parts))


def best3(pool):
    seen, out = set(), []
    for t in sorted(pool, key=lambda t: t["reads"]):
        if t["chash"] in seen:
            continue
        seen.add(t["chash"])
        out.append(t)
        if len(out) == 3:
            break
    return out


def main():
    with open(os.path.join(tools.ROOT, "prompts", "F2_template.txt"), "w") as f:
        f.write(TEMPLATE + "\n")
    # reference scores for context
    refdir = os.path.join(os.path.dirname(tools.ROOT), "round-1/experiment-1/src/tasks/t1_grid/references")
    refs = {fn: tools.run_tests(open(os.path.join(refdir, fn)).read(), count_reads=True)["reads"]
            for fn in sorted(os.listdir(refdir))}
    # seeds: 3 best distinct stage A programs
    pool = []
    for l in open(os.path.join(tools.ROOT, "results", "stageA.jsonl")):
        r = json.loads(l)
        if r["pass_all"]:
            s = tools.run_tests(r["code"], count_reads=True)["reads"]
            if s is not None:
                pool.append(dict(id=r["id"], code=r["code"], reads=s, chash=r["chash"]))
    top = best3(pool)
    state = dict(reference_scores=refs, rounds=[dict(round=0, top=[dict(id=t["id"], reads=t["reads"]) for t in top])])
    print("refs", refs)
    print("round 0 top", [(t["id"], t["reads"]) for t in top], flush=True)
    import gen
    lm = gen.LM()
    torch.manual_seed(SEED)
    open(OUT, "w").close()
    for rnd in range(1, ROUNDS + 1):
        prompt = render(top)
        pid = lm.prompt_ids([{"role": "user", "content": prompt}])
        outs = []
        for _ in range(2):  # two half-batches: the prompt holds three programs
            outs += gen.safe_generate(lm, [pid] * (PER_ROUND // 2), max_new_tokens=700)
        new = []
        with open(OUT, "a") as f:
            for i, o in enumerate(outs):
                row = dict(id=f"F2-r{rnd}-{i}", stage="F2", round=rnd, shown=[t["id"] for t in top], text=o["text"],
                           n_new=o["n_new"])
                row.update(tools.evaluate(o["text"]))
                row["reads"] = tools.run_tests(row["code"], count_reads=True)["reads"] if row["pass_all"] else None
                f.write(json.dumps(row) + "\n")
                if row["reads"] is not None:
                    new.append(dict(id=row["id"], code=row["code"], reads=row["reads"], chash=row["chash"]))
        top = best3(top + new)
        state["rounds"].append(dict(round=rnd, n_valid=len(new), new_scores=sorted(round(t["reads"], 1) for t in new),
                                    top=[dict(id=t["id"], reads=t["reads"]) for t in top]))
        json.dump(state, open(STATE, "w"), indent=1)
        print(f"round {rnd}: valid {len(new)}/8, top {[(t['id'], round(t['reads'], 1)) for t in top]}", flush=True)


if __name__ == "__main__":
    main()
