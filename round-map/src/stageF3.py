"""Stage F3: reject repeats. 5 conversations of up to 8 steps. Feedback never names a method.
usage: python src/stageF3.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch
import tools

SEED, CHAINS, STEPS = 1008, 5, 8
OUT = os.path.join(tools.ROOT, "results", "stageF3.jsonl")
REPEAT = "Rejected: this works the same way as your attempt #{k}. Write a solution that works in a fundamentally different way."
FAIL = "Rejected: it fails the tests ({n} of 46 pass). Fix it or try another approach."
ACCEPT = "Accepted. Now write another solution that works in a fundamentally different way from all your previous ones."


def main():
    with open(os.path.join(tools.ROOT, "prompts", "F3_feedback.txt"), "w") as f:
        f.write("step 1: {SPEC}\n\nsame signature as attempt k: " + REPEAT + "\n\nfails tests: " + FAIL +
                "\n\nnew signature and passes: " + ACCEPT + "\n")
    import gen
    lm = gen.LM()
    torch.manual_seed(SEED)
    convs = [[{"role": "user", "content": tools.SPEC}] for _ in range(CHAINS)]
    sigs = [[] for _ in range(CHAINS)]
    open(OUT, "w").close()
    for step in range(1, STEPS + 1):
        pids = [lm.prompt_ids(c) for c in convs]
        # two half-batches: the conversations get long
        outs = []
        for b0 in range(0, CHAINS, 3):
            outs += lm.generate(pids[b0:b0 + 3], max_new_tokens=700)
        with open(OUT, "a") as f:
            for c, o in enumerate(outs):
                ev = tools.evaluate(o["text"])
                if ev["sig"] in sigs[c]:
                    k = sigs[c].index(ev["sig"]) + 1
                    verdict, fb = "repeat", REPEAT.format(k=k)
                elif not ev["pass_all"]:
                    verdict, fb = "fail", FAIL.format(n=ev["n_passed"])
                else:
                    verdict, fb = "accepted", ACCEPT
                sigs[c].append(ev["sig"])
                row = dict(id=f"F3-c{c}-s{step}", stage="F3", chain=c, step=step, verdict=verdict, feedback=fb,
                           text=o["text"], n_new=o["n_new"], prompt_tokens=len(pids[c]))
                row.update(ev)
                f.write(json.dumps(row) + "\n")
                convs[c] += [{"role": "assistant", "content": o["text"]}, {"role": "user", "content": fb}]
                print(step, c, verdict, ev["sig"], ev["n_passed"], flush=True)


if __name__ == "__main__":
    main()
