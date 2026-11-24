"""Child-process harness. Run ONLY as:  python -I -S harness.py <first_case_index> <count_reads 0/1>
stdin: JSON {"code": str, "tests": [...]}.  stdout: one JSON line per finished case.
On a per-case timeout it prints the timeout row and exits; the parent restarts it at the next case.
Never import this file from the parent process.
"""
import sys, os, json, threading, time

PER_CASE = 2.0
READS = [0]


class Row(str):
    """A grid row that counts cell reads (used only for the F2 score)."""
    __slots__ = ()

    def __getitem__(self, k):
        if isinstance(k, slice):
            READS[0] += len(range(*k.indices(len(self))))
        else:
            READS[0] += 1
        return str.__getitem__(self, k)

    def __iter__(self):
        for i in range(len(self)):
            READS[0] += 1
            yield str.__getitem__(self, i)


def check(case, out):
    start, goal, grid = tuple(case["start"]), tuple(case["goal"]), case["grid"]
    if not isinstance(out, (list, tuple)):
        return False, "not a list"
    if not case["reachable"]:
        return (len(out) == 0), ("ok" if len(out) == 0 else "path for unreachable")
    if len(out) == 0:
        return False, "empty for reachable"
    try:
        path = [(int(p[0]), int(p[1])) for p in out]
        if any(len(p) != 2 for p in out):
            return False, "bad cell"
    except Exception:
        return False, "bad cell"
    if path[0] != start or path[-1] != goal:
        return False, "bad endpoints"
    R, C = len(grid), len(grid[0])
    for (r, c) in path:
        if not (0 <= r < R and 0 <= c < C) or grid[r][c] != ".":
            return False, "cell not free"
    for a, b in zip(path, path[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            return False, "not neighbours"
    return True, "ok"


def main():
    first = int(sys.argv[1])
    count = sys.argv[2] == "1"
    job = json.loads(sys.stdin.read())
    real_out = os.fdopen(os.dup(1), "w")
    devnull = open(os.devnull, "w")
    sys.stdout = devnull
    sys.stderr = devnull
    sys.setrecursionlimit(200000)
    threading.stack_size(256 * 1024 * 1024)

    def emit(row):
        real_out.write(json.dumps(row) + "\n")
        real_out.flush()

    ns = {"__name__": "candidate"}
    box = {}

    def load():
        try:
            exec(compile(job["code"], "<candidate>", "exec"), ns)
            box["ok"] = callable(ns.get("solve"))
            if not box["ok"]:
                box["err"] = "no solve"
        except BaseException as e:
            box["ok"] = False
            box["err"] = "load: %s: %s" % (type(e).__name__, str(e)[:200])

    t = threading.Thread(target=load, daemon=True)
    t.start()
    t.join(PER_CASE)
    if t.is_alive() or not box.get("ok"):
        emit({"fatal": box.get("err", "load timeout")})
        real_out.flush()
        os._exit(0)
    solve = ns["solve"]

    tests = job["tests"]
    for i in range(first, len(tests)):
        case = tests[i]
        res = {}

        def run():
            try:
                if count:
                    g = [Row(r) for r in case["grid"]]
                else:
                    g = list(case["grid"])
                READS[0] = 0
                res["out"] = solve(g, tuple(case["start"]), tuple(case["goal"]))
                res["reads"] = READS[0]
            except BaseException as e:
                res["err"] = "%s: %s" % (type(e).__name__, str(e)[:120])

        t0 = time.time()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(PER_CASE)
        if t.is_alive():
            emit({"i": i, "passed": False, "why": "timeout", "plen": None, "reads": None})
            real_out.flush()
            os._exit(0)
        if "err" in res:
            emit({"i": i, "passed": False, "why": res["err"], "plen": None, "reads": None})
            continue
        try:
            ok, why = check(case, res["out"])
            plen = len(res["out"]) if ok else None
        except BaseException as e:
            ok, why, plen = False, "check: %s" % type(e).__name__, None
        emit({"i": i, "passed": ok, "why": why, "plen": plen, "reads": res.get("reads") if count else None,
              "t": round(time.time() - t0, 4)})
    real_out.flush()
    os._exit(0)


main()
