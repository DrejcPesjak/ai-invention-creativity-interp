"""Single-turn stages: A, B, C, E, F1.   usage: python src/stages.py <A|B|C|E|F1> [--write-prompts-only] [--default BFS]
Prompts are written to prompts/ before any generation."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools, catalogue

SEEDS = {"A": 1001, "B": 1002, "C": 1003, "E": 1005, "F1": 1006}
SPEC = tools.SPEC
TASK_PART, FORMAT_PART = SPEC.split("\n\n")
B_SUFFIX = ("Do not write code. List every different algorithm or approach that could solve this task, "
            "one per line, with a one-sentence description.")


def prompts_for(stage, default="BFS"):
    """returns list of (prompt_key, prompt_text, n_samples, meta)"""
    cat = catalogue.load()
    out = []
    if stage == "A":
        out.append(("A_unprompted", SPEC, 50, {}))
    elif stage == "B":
        out.append(("B_list", SPEC + "\n\n" + B_SUFFIX, 10, {}))
    elif stage == "C":
        for k, m in cat.items():
            out.append((f"C_{k}", f"Implement this task using {m['name']}.\n\n{SPEC}", 10, dict(target=k, level="H3")))
    elif stage == "E":
        for k, m in cat.items():
            if k == default:
                continue
            out.append((f"E_H1_{k}", f"{SPEC}\n\nUse the approach whose name starts with the letter '{m['letter']}'.",
                        10, dict(target=k, level="H1")))
            nm = m["name"][0].upper() + m["name"][1:]
            out.append((f"E_H2_{k}", f"{SPEC}\n\n{nm} is one well-known approach to this task; implement any correct algorithm.",
                        10, dict(target=k, level="H2")))
            out.append((f"E_H4_{k}", f"{SPEC}\n\nHow it must work: {m['mech']}", 10, dict(target=k, level="H4")))
            if m.get("pseudo"):
                out.append((f"E_H5_{k}", f"{SPEC}\n\nFollow this pseudo-code:\n{m['pseudo']}", 10, dict(target=k, level="H5")))
    elif stage == "F1":
        for k, m in cat.items():
            if k == default or not m.get("f1"):
                continue
            out.append((f"F1_{k}", f"{TASK_PART}\n\nAdditional requirement: {m['f1']}\n\n{FORMAT_PART}", 10,
                        dict(target=k)))
    return out


def main():
    stage = sys.argv[1]
    default = sys.argv[sys.argv.index("--default") + 1] if "--default" in sys.argv else "BFS"
    ps = prompts_for(stage, default)
    for key, text, n, meta in ps:
        with open(os.path.join(tools.ROOT, "prompts", key + ".txt"), "w") as f:
            f.write(text + "\n")
    print(f"wrote {len(ps)} prompts for stage {stage}")
    if "--write-prompts-only" in sys.argv:
        return
    import gen
    jobs = []
    for key, text, n, meta in ps:
        for i in range(n):
            jobs.append(dict(id=f"{key}-{i}", stage=stage, prompt_key=key,
                             messages=[{"role": "user", "content": text}], **meta))
    lm = gen.LM()
    gen.run_jobs(lm, jobs, os.path.join(tools.ROOT, "results", f"stage{stage}.jsonl"), batch=12, seed=SEEDS[stage],
                 evaluate=(stage != "B"))


if __name__ == "__main__":
    main()
