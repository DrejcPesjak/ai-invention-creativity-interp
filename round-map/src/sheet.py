"""Build the blind judging sheet (PLAN 5.4).
results/judging_sheet.jsonl : sid, group, code, n_passed, shortest_all   (shuffled; no stage, no prompt)
results/sheet_key.json      : sid -> list of row ids ; NOT to be read while judging
Identical programs (comments/whitespace stripped) share one sid. `group` is an opaque id for
(prompt, signature): the plan allows labelling a group by reading 3 of its programs.
usage: python src/sheet.py"""
import glob, hashlib, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools

R = os.path.join(tools.ROOT, "results")
FILES = ["stage0", "stageA", "stageC", "stageD_rollouts", "stageE", "stageF1", "stageF2", "stageF3"]
rng = random.Random(4242)
progs, key = {}, {}
for name in FILES:
    p = os.path.join(R, name + ".jsonl")
    if not os.path.exists(p):
        print("missing", name)
        continue
    for l in open(p):
        r = json.loads(l)
        if not r.get("code"):
            continue
        h = r["chash"]
        pk = r.get("prompt_key") or (f"D-{r.get('node')}-{r.get('pos')}-{r.get('token')}" if name.startswith("stageD")
                                    else name)
        g = hashlib.sha1(f"salt9|{pk}|{r['sig']}".encode()).hexdigest()[:8]
        if h not in progs:
            progs[h] = dict(code=r["code"], n_passed=r["n_passed"], shortest_all=r["shortest_all"], group=g)
            key[h] = []
        key[h].append(r["id"])
items = list(progs.items())
rng.shuffle(items)
sid_of = {}
with open(os.path.join(R, "judging_sheet.jsonl"), "w") as f:
    for i, (h, p) in enumerate(items):
        sid = f"P{i:04d}"
        sid_of[h] = sid
        f.write(json.dumps(dict(sid=sid, **p)) + "\n")
json.dump({sid_of[h]: ids for h, ids in key.items()}, open(os.path.join(R, "sheet_key.json"), "w"))
print("rows with code:", sum(len(v) for v in key.values()), "distinct programs:", len(items),
      "groups:", len({p["group"] for p in progs.values()}))
