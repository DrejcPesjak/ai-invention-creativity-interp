"""Stage G join: labels -> stages -> the map. Writes results/labels.jsonl, results/joined.jsonl, results/summary.json.
usage: python src/report.py"""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tools, catalogue

R = os.path.join(tools.ROOT, "results")
CAT = catalogue.load()
NO_METHODS = {k for k, m in CAT.items() if not m["pure_ok"]}  # faithful-but-failing counts as RIGHT
# IDDFS: a textbook version (cycle check on the current path only) is exponential on open grids and times out
# in this runner (my own implementation of the H5 pseudo-code passes 34/46), so it is treated the same way.
NO_METHODS.add("IDDFS")
DEFAULT = "BFS"


def jl(name):
    p = os.path.join(R, name)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


# ---- final label per sheet id: home judge, then my adjudication file on top
sheet = {r["sid"]: r for r in jl("judging_sheet.jsonl")}
overlap = set(json.load(open(os.path.join(R, "judge", "overlap_sids.json"))))
votes = collections.defaultdict(list)
for k in range(8):
    for x in jl(f"judge/labels_{k}.jsonl"):
        x["judge"] = k
        votes[x["sid"]].append(x)
adj = {x["sid"]: x for x in jl("judge/adjudication.jsonl")}
final = {}
for sid, v in votes.items():
    f = dict(v[0])
    f["n_judges"] = len(v)
    f["judges_agree"] = len({(x["label"], x["faithful"]) for x in v}) == 1
    if sid in adj:
        f.update(label=adj[sid]["label"], faithful=adj[sid]["faithful"], note=adj[sid].get("note", f["note"]),
                 adjudicated=True)
    final[sid] = f
with open(os.path.join(R, "labels.jsonl"), "w") as fo:
    for sid in sorted(final):
        fo.write(json.dumps(final[sid]) + "\n")
key = json.load(open(os.path.join(R, "sheet_key.json")))
row2sid = {rid: sid for sid, ids in key.items() for rid in ids}


def lab(row):
    """row -> (label, faithful). No code -> JUNK."""
    sid = row2sid.get(row["id"])
    if not row.get("code") or sid is None:
        return "JUNK", False, None
    f = final[sid]
    return f["label"], bool(f["faithful"]), sid


def outcome(row, target):
    l, faithful, _ = lab(row)
    if l == "JUNK":
        return "JUNK"
    if l != target:
        return "SWAPPED"
    if row["pass_all"] or (target in NO_METHODS and faithful):
        return "RIGHT"
    return "BROKEN"


joined = []
for name in ["stage0", "stageA", "stageC", "stageD_rollouts", "stageE", "stageF1", "stageF2", "stageF3"]:
    for r in jl(name + ".jsonl"):
        l, faithful, sid = lab(r)
        d = {k: r.get(k) for k in ("id", "stage", "prompt_key", "target", "level", "n_passed", "pass_all",
                                   "shortest_all", "n_strict", "strict_all", "sig", "chain", "step", "verdict",
                                   "round", "node", "pos", "token_text", "reads")}
        d.update(file=name, sid=sid, label=l, faithful=faithful)
        if r.get("target"):
            d["outcome"] = outcome(r, r["target"])
        joined.append(d)
with open(os.path.join(R, "joined.jsonl"), "w") as fo:
    for d in joined:
        fo.write(json.dumps(d) + "\n")

S = {}
by_file = collections.defaultdict(list)
for d in joined:
    by_file[d["file"]].append(d)

# A
A = by_file["stageA"]
S["A_labels"] = dict(collections.Counter(d["label"] for d in A))
S["A_pass_core"] = sum(d["pass_all"] for d in A)
S["A_pass_strict"] = sum(bool(d["strict_all"]) for d in A)
S["A_right"] = {m: sum(1 for d in A if d["label"] == m and (d["pass_all"] or (m in NO_METHODS and d["faithful"])))
                for m in CAT}


def cell(rows):
    c = collections.Counter(d["outcome"] for d in rows)
    return [c.get("RIGHT", 0), c.get("BROKEN", 0), c.get("SWAPPED", 0), c.get("JUNK", 0)]


def swapped_to(rows):
    return dict(collections.Counter(d["label"] for d in rows if d["outcome"] == "SWAPPED").most_common())


# C
S["C"], S["C_swapped_to"], S["KNOWN"] = {}, {}, {}
for m in CAT:
    rows = [d for d in by_file["stageC"] if d["target"] == m]
    S["C"][m] = cell(rows)
    S["C_swapped_to"][m] = swapped_to(rows)
    S["KNOWN"][m] = S["C"][m][0] >= 3
# E ladder
S["E"], S["E_swapped_to"], S["lowest_level"] = {}, {}, {}
for m in CAT:
    if m == DEFAULT:
        continue
    lad = {}
    lad["H0"] = [S["A_right"][m], len(A)]
    for lv in ("H1", "H2", "H4", "H5"):
        rows = [d for d in by_file["stageE"] if d["target"] == m and d["level"] == lv]
        lad[lv] = cell(rows)
        S["E_swapped_to"][f"{lv}_{m}"] = swapped_to(rows)
    lad["H3"] = S["C"][m]
    S["E"][m] = lad
    low = "never"
    for lv in ("H0", "H1", "H2", "H3", "H4", "H5"):
        ok = (lad[lv][0] * 2 >= lad[lv][1]) if lv == "H0" else (lad[lv][0] >= 5)
        if ok:
            low = lv
            break
    S["lowest_level"][m] = low
# F1
S["F1"], S["F1_labels"] = {}, {}
for m in CAT:
    rows = [d for d in by_file["stageF1"] if d["target"] == m]
    if rows:
        S["F1"][m] = cell(rows)
        S["F1_labels"][m] = dict(collections.Counter(
            d["label"] + ("" if d["pass_all"] else "*") for d in rows).most_common())
# F2
F2 = by_file["stageF2"]
S["F2_labels"] = dict(collections.Counter(d["label"] for d in F2))
S["F2_rounds"] = json.load(open(os.path.join(R, "stageF2_rounds.json"))) if os.path.exists(
    os.path.join(R, "stageF2_rounds.json")) else None
# F3
S["F3_chains"] = {}
for c in range(5):
    rows = sorted([d for d in by_file["stageF3"] if d["chain"] == c], key=lambda d: d["step"])
    S["F3_chains"][c] = [dict(step=d["step"], label=d["label"], verdict=d["verdict"], n_passed=d["n_passed"],
                              faithful=d["faithful"], sig=d["sig"]) for d in rows]
S["F3_accepted"] = dict(collections.Counter(d["label"] for d in by_file["stageF3"] if d["verdict"] == "accepted"))
S["F3_right_any"] = dict(collections.Counter(
    d["label"] for d in by_file["stageF3"] if d["pass_all"] or (d["label"] in NO_METHODS and d["faithful"])))
# D
S["D_labels"] = dict(collections.Counter((d["label"] + ("" if d["pass_all"] else "*")) for d in by_file["stageD_rollouts"]))
S["D_by_branch"] = {}
for d in by_file["stageD_rollouts"]:
    k = f"{d['node']}@{d['pos']}:{d['token_text']!r}"
    S["D_by_branch"].setdefault(k, []).append(d["label"] + ("" if d["pass_all"] else "*"))
# judging stats
S["judging"] = dict(distinct_programs=len(sheet), labels=dict(collections.Counter(f["label"] for f in final.values())),
                    overlap=len([s for s in final if final[s]["n_judges"] > 1]),
                    overlap_label_agree=sum(1 for s, v in votes.items() if len(v) > 1 and len({x["label"] for x in v}) == 1),
                    adjudicated=len(adj), unfaithful=sum(1 for f in final.values() if not f["faithful"]))
# right-but-unfaithful (plan's RIGHT = label + pass; how many of those did the judge call not faithful)
S["right_but_unfaithful"] = dict(collections.Counter(
    d["target"] for d in joined if d.get("outcome") == "RIGHT" and not d["faithful"]))
# OTHER that pass
S["other_passing"] = sorted({d["sid"] for d in joined if d["label"] == "OTHER" and d["pass_all"]})
json.dump(S, open(os.path.join(R, "summary.json"), "w"), indent=1)

lm = json.load(open(os.path.join(R, "stageB_mapping.json")))["listed_of_10"]
print("A:", S["A_labels"], "pass core", S["A_pass_core"], "strict", S["A_pass_strict"])
print(f"{'method':8s} listed  A/50  C[R,B,S,J]      KNOWN low    H1            H2            H4            H5            F1")
for m in CAT:
    e = S["E"].get(m, {})
    print(f"{m:8s} {lm.get(m, 0):>4}  {S['A_labels'].get(m, 0):>4}  {str(S['C'][m]):15s} {str(S['KNOWN'][m]):5s} "
          f"{S['lowest_level'].get(m, '-'):6s} " + " ".join(f"{str(e.get(l, '')):13s}" for l in ("H1", "H2", "H4", "H5"))
          + f" {S['F1'].get(m, '')}")
print("C swapped to:", S["C_swapped_to"])
print("F1 labels:", json.dumps(S["F1_labels"]))
print("F2:", S["F2_labels"])
for c, ch in S["F3_chains"].items():
    print("F3 chain", c, [(x["label"], x["verdict"][0], x["n_passed"]) for x in ch])
print("D:", json.dumps(S["D_by_branch"]))
print("right but unfaithful:", S["right_but_unfaithful"])
print("OTHER passing:", S["other_passing"])
print("judging:", S["judging"])
