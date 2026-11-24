"""Stage D: the tree, built level by level. One model per process.
usage: python src/stageD.py pass1|pass2|pass3 <level>      (run by src/run_stageD.sh)
Files in results/D/: open_<L>.json, pass1_<L>.json, pass2_<L>.json, walk_<L>.json
      results/stageD_rollouts.jsonl (every rollout), results/stageD_leaves.jsonl, results/stageD_points.jsonl
"""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch
import tools, gen

SURE, MIN_P, K, R, MAX_FORKS, MAX_POINTS, MAX_ROLLOUTS = 0.90, 0.03, 5, 4, 3, 15, 800
MAX_NEW = 700
SEED = 1004
D = os.path.join(tools.ROOT, "results", "D")
os.makedirs(D, exist_ok=True)
ROLL = os.path.join(tools.ROOT, "results", "stageD_rollouts.jsonl")
LEAVES = os.path.join(tools.ROOT, "results", "stageD_leaves.jsonl")
POINTS = os.path.join(tools.ROOT, "results", "stageD_points.jsonl")
MSGS = [{"role": "user", "content": tools.SPEC}]


def jl(path):
    return [json.loads(l) for l in open(path)] if os.path.exists(path) else []


def pass1(L):
    """tuned: greedy completion of every open prefix, hesitation points."""
    if L == 0:
        json.dump([dict(node="n0", prefix=[], mass_tuned=1.0, mass_base=1.0, forks=0, parent=None,
                        fork_pos=None, token=None)], open(f"{D}/open_0.json", "w"))
    opened = json.load(open(f"{D}/open_{L}.json"))
    lm = gen.LM(gen.TUNED)
    pid = lm.prompt_ids(MSGS)
    out = []
    for b0 in range(0, len(opened), 4):
        chunk = opened[b0:b0 + 4]
        res = lm.generate([pid] * len(chunk), forced=[n["prefix"] for n in chunk], sample=False, want_probs=True,
                          max_new_tokens=max(MAX_NEW - min(len(n["prefix"]) for n in chunk), 1))
        for n, r in zip(chunk, res):
            ids = r["ids"][:MAX_NEW]
            off = len(n["prefix"])
            pts = []
            for s, st in enumerate(r["steps"]):
                pos = off + s
                if pos >= len(ids):
                    break
                if st["p"] < SURE and len(pts) < MAX_POINTS:
                    pts.append(dict(pos=pos, top1=st["id"], p_top1=st["p"], tuned_top=st["top"]))
            ev = tools.evaluate(r["text"])
            out.append(dict(node=n["node"], greedy_ids=ids, greedy_text=lm.tok.decode(ids, skip_special_tokens=True),
                            points=pts, n_hesitation_total=sum(1 for st in r["steps"] if st["p"] < SURE),
                            greedy_eval=ev))
            print(n["node"], "greedy len", len(ids), "points", len(pts), "sig", ev["sig"], flush=True)
    json.dump(dict(prompt_ids=pid, nodes=out), open(f"{D}/pass1_{L}.json", "w"))


def pass2(L):
    """base: next-token probabilities at every point; candidate tokens."""
    p1 = json.load(open(f"{D}/pass1_{L}.json"))
    lm = gen.LM(gen.BASE)
    pid = p1["prompt_ids"]
    jobs = [(n, pt) for n in p1["nodes"] for pt in n["points"]]
    out = []
    for b0 in range(0, len(jobs), 8):
        chunk = jobs[b0:b0 + 8]
        res = lm.next_probs([pid + n["greedy_ids"][:pt["pos"]] for n, pt in chunk], k=K)
        for (n, pt), r in zip(chunk, res):
            cands = [[i, p] for i, p in r["top"] if p >= MIN_P]
            if pt["top1"] not in [c[0] for c in cands]:
                cands.append([pt["top1"], float(r["full"][pt["top1"]])])
            out.append(dict(node=n["node"], pos=pt["pos"], cands=cands, base_top=r["top"],
                            base_p_tuned_top1=float(r["full"][pt["top1"]])))
    json.dump(out, open(f"{D}/pass2_{L}.json", "w"))
    print("points", len(out), "candidate tokens", sum(len(o["cands"]) for o in out))


def pass3(L):
    """tuned: R rollouts per (point, candidate); then walk the points and build the next level."""
    opened = {n["node"]: n for n in json.load(open(f"{D}/open_{L}.json"))}
    p1 = json.load(open(f"{D}/pass1_{L}.json"))
    p2 = {(o["node"], o["pos"]): o for o in json.load(open(f"{D}/pass2_{L}.json"))}
    pid = p1["prompt_ids"]
    nodes = sorted(p1["nodes"], key=lambda n: -opened[n["node"]]["mass_tuned"])
    lm = gen.LM(gen.TUNED)

    # tuned probability of every candidate token
    flat = [(n, pt) for n in nodes for pt in n["points"]]
    for b0 in range(0, len(flat), 8):
        chunk = flat[b0:b0 + 8]
        res = lm.next_probs([pid + n["greedy_ids"][:pt["pos"]] for n, pt in chunk], k=K)
        for (n, pt), r in zip(chunk, res):
            o = p2[(n["node"], pt["pos"])]
            o["p_tuned"] = {str(t): float(r["full"][t]) for t, _ in o["cands"]}

    done = {r["id"]: r for r in jl(ROLL)}
    used_before = sum(1 for r in done.values() if r["level"] != L)
    budget = MAX_ROLLOUTS - used_before
    jobs, skipped_points = [], 0
    for n in nodes:
        for pt in n["points"]:
            o = p2[(n["node"], pt["pos"])]
            need = len(o["cands"]) * R
            if len(jobs) + need > budget:
                skipped_points += 1
                o["skipped"] = True
                continue
            for t, pb in o["cands"]:
                for k in range(R):
                    jobs.append(dict(id=f"D-{n['node']}-{pt['pos']}-{t}-{k}", stage="D", level=L, node=n["node"],
                                     pos=pt["pos"], token=t, forced=n["greedy_ids"][:pt["pos"]] + [t]))
    todo = [j for j in jobs if j["id"] not in done]
    todo.sort(key=lambda j: len(j["forced"]))
    print(f"level {L}: budget {budget}, rollouts planned {len(jobs)}, to run {len(todo)}, points skipped {skipped_points}",
          flush=True)
    torch.manual_seed(SEED + L * 10000 + len(done))
    for b0 in range(0, len(todo), 12):
        chunk = todo[b0:b0 + 12]
        res = gen.safe_generate(lm, [pid] * len(chunk), forced=[j["forced"] for j in chunk],
                          max_new_tokens=max(MAX_NEW - min(len(j["forced"]) for j in chunk), 1))
        with open(ROLL, "a") as f:
            for j, r in zip(chunk, res):
                row = dict(j)
                row.update(text=r["text"], n_new=r["n_new"], token_text=lm.tok.decode([j["token"]]))
                del row["forced"]
                row.update(tools.evaluate(r["text"]))
                f.write(json.dumps(row) + "\n")
                done[row["id"]] = row
        print(f"  rollouts {b0 + len(chunk)}/{len(todo)}", flush=True)

    # ---- walk ----
    def majority(sigs):
        c = collections.Counter(sigs).most_common()
        best = [s for s, k in c if k == c[0][1]]
        return sorted(best)[0]

    nxt, leaves, points_out = [], [], []
    for n in nodes:
        node = opened[n["node"]]
        mt, mb = node["mass_tuned"], node["mass_base"]
        child_i = 0
        for pt in n["points"]:
            o = p2[(n["node"], pt["pos"])]
            if o.get("skipped"):
                points_out.append(dict(level=L, node=n["node"], pos=pt["pos"], kind="not run (budget)"))
                continue
            opts = {}
            for t, pb in o["cands"]:
                sigs = [done[f"D-{n['node']}-{pt['pos']}-{t}-{k}"]["sig"] for k in range(R)]
                opts[t] = dict(sigs=sigs, maj=majority(sigs), p_base=pb, p_tuned=o["p_tuned"][str(t)],
                               text=lm.tok.decode([t]))
            majs = {v["maj"] for v in opts.values()}
            ctx = lm.tok.decode(n["greedy_ids"][max(0, pt["pos"] - 12):pt["pos"]])
            rec = dict(level=L, node=n["node"], pos=pt["pos"], context=ctx, tuned_top1=lm.tok.decode([pt["top1"]]),
                       p_top1=pt["p_top1"],
                       options=[dict(token=v["text"], token_id=t, p_base=v["p_base"], p_tuned=v["p_tuned"],
                                     sigs=v["sigs"], maj=v["maj"]) for t, v in opts.items()])
            if len(majs) == 1:
                rec["kind"] = "wording"
                points_out.append(rec)
                continue
            rec["kind"] = "fork"
            # does the fork change the static (method-like) part of the signature, or only pass/shortest flags?
            rec["flags_differ"] = len({m[2:] for m in majs}) > 1
            main = opts[pt["top1"]]["maj"]
            off_t = off_b = 0.0
            rec["branches"] = []
            for g in sorted(majs):
                if g == main:
                    continue
                grp = {t: v for t, v in opts.items() if v["maj"] == g}
                t = max(grp, key=lambda t: grp[t]["p_base"])  # most probable under the proposing (base) model
                v = grp[t]
                bt, bb = mt * v["p_tuned"], mb * sum(x["p_base"] for x in grp.values())
                off_t += sum(x["p_tuned"] for x in grp.values())
                off_b += sum(x["p_base"] for x in grp.values())
                agree = len(set(v["sigs"])) == 1
                br = dict(token=v["text"], token_id=t, maj=g, agree=agree, mass_tuned=bt, mass_base=bb)
                base = dict(level=L, parent=n["node"], fork_pos=pt["pos"], token=v["text"], token_id=t,
                            mass_tuned=bt, mass_base=bb, context=ctx,
                            rollout_ids=[f"D-{n['node']}-{pt['pos']}-{t}-{k}" for k in range(R)])
                if agree:
                    br["fate"] = "leaf"
                    leaves.append(dict(base, kind="leaf", sig=g))
                elif node["forks"] < MAX_FORKS:
                    child = f"{n['node']}.{child_i}"
                    child_i += 1
                    br["fate"] = "opened " + child
                    nxt.append(dict(node=child, prefix=n["greedy_ids"][:pt["pos"]] + [t], mass_tuned=bt, mass_base=bb,
                                    forks=node["forks"] + 1, parent=n["node"], fork_pos=pt["pos"], token=v["text"]))
                else:
                    br["fate"] = "mixed leaf (max depth)"
                    leaves.append(dict(base, kind="mixed leaf (max depth)", sig=g))
                rec["branches"].append(br)
            mt *= max(0.0, 1 - off_t)
            mb *= max(0.0, 1 - off_b)
            points_out.append(rec)
        leaves.append(dict(level=L, parent=node["parent"], node=n["node"], kind="greedy leaf", fork_pos=node["fork_pos"],
                           token=node["token"], mass_tuned=mt, mass_base=mb, sig=n["greedy_eval"]["sig"],
                           greedy_id=f"Dg-{n['node']}"))
        # the greedy completion is a program too: goes to the judging sheet through the rollouts file
        gid = f"Dg-{n['node']}"
        if gid not in done:
            row = dict(id=gid, stage="D", level=L, node=n["node"], pos=None, token=None, text=n["greedy_text"],
                       greedy=True)
            row.update(n["greedy_eval"])
            with open(ROLL, "a") as f:
                f.write(json.dumps(row) + "\n")
            done[gid] = row
    with open(LEAVES, "a") as f:
        for l in leaves:
            f.write(json.dumps(l) + "\n")
    with open(POINTS, "a") as f:
        for p in points_out:
            f.write(json.dumps(p) + "\n")
    used = sum(1 for r in done.values() if not r.get("greedy"))
    if used >= MAX_ROLLOUTS - R * 2 and nxt:
        print(f"MAX_ROLLOUTS reached ({used}); {len(nxt)} open prefixes are not expanded")
        json.dump(nxt, open(f"{D}/unexpanded_{L + 1}.json", "w"))
        nxt = []
    json.dump(nxt, open(f"{D}/open_{L + 1}.json", "w"))
    kinds = collections.Counter(p["kind"] for p in points_out)
    print(f"level {L}: points {dict(kinds)}; leaves {len(leaves)}; next level open {len(nxt)}; rollouts used {used}")


if __name__ == "__main__":
    {"pass1": pass1, "pass2": pass2, "pass3": pass3}[sys.argv[1]](int(sys.argv[2]))
