"""run_tests, signature, code extraction, normalisation. No model code here."""
import ast, io, json, os, re, resource, subprocess, sys, time, tokenize, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS = os.path.join(ROOT, "src", "harness.py")
PY = "/home/drew99/venvs/ml/bin/python"
SPEC = open(os.path.join(ROOT, "task", "spec.txt")).read().strip()
TESTS = json.load(open(os.path.join(ROOT, "task", "tests.json")))
TOTAL_LIMIT = 20.0
# Owner's decision after stage 0: "pass" means the 46 core cases. The two cases where start == goal sits on a
# wall are still run and recorded (n_strict, strict_all) but do not count for pass_all.
NON_CORE = {"one_by_one_wall", "start_equals_goal_wall"}
CORE = [i for i, t in enumerate(TESTS) if t["id"] not in NON_CORE]
N_CORE = len(CORE)
MEM = 1 << 30


def _limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEM, MEM))
    resource.setrlimit(resource.RLIMIT_NPROC, (64, 64)) if False else None
    os.setsid()


def extract_code(text):
    """First ```python block containing 'def solve'. Falls back to an unterminated block (truncated answer)."""
    for m in re.finditer(r"```(?:python|py)?[ \t]*\n(.*?)```", text, re.S):
        if "def solve" in m.group(1):
            return m.group(1).strip("\n")
    m = re.search(r"```(?:python|py)?[ \t]*\n(.*)$", text, re.S)
    if m and "def solve" in m.group(1) and "```" not in m.group(1):
        return m.group(1).strip("\n")  # truncated: will normally fail to parse or fail tests
    return None


def run_tests(code, count_reads=False):
    """Run code on the 48 cases in sandboxed child processes. Returns a dict."""
    n = len(TESTS)
    rows = [None] * n
    fatal = None
    if not code:
        return dict(n_passed=0, pass_all=False, shortest_all=False, fatal="no code", fails=[], reads=None,
                    n_strict=0, strict_all=False)
    payload = json.dumps({"code": code, "tests": TESTS})
    t0 = time.time()
    i = 0
    while i < n:
        left = TOTAL_LIMIT - (time.time() - t0)
        if left <= 0:
            break
        try:
            p = subprocess.run([PY, "-I", "-S", HARNESS, str(i), "1" if count_reads else "0"],
                               input=payload, capture_output=True, text=True, timeout=left + 1,
                               preexec_fn=_limits, cwd="/tmp", env={})
            out = p.stdout
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        last = i - 1
        for line in out.splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "fatal" in r:
                fatal = r["fatal"]
                break
            rows[r["i"]] = r
            last = max(last, r["i"])
        if fatal:
            break
        if last < i:  # child died without reporting case i (crash / memory): count it failed, move on
            rows[i] = {"i": i, "passed": False, "why": "crash", "plen": None, "reads": None}
            last = i
        i = last + 1
    for k in range(n):
        if rows[k] is None:
            rows[k] = {"i": k, "passed": False, "why": fatal or "total time limit", "plen": None, "reads": None}
    n_strict = sum(r["passed"] for r in rows)
    n_passed = sum(rows[i]["passed"] for i in CORE)
    pass_all = n_passed == N_CORE
    shortest_all = pass_all and all(
        (rows[i]["plen"] == TESTS[i]["shortest_len"]) if TESTS[i]["reachable"] else True for i in CORE)
    reads = None
    if count_reads and pass_all:
        reads = sum(rows[i]["reads"] for i in CORE) / N_CORE
    fails = [(TESTS[r["i"]]["id"], r["why"]) for r in rows if not r["passed"] and r["i"] in CORE][:6]
    return dict(n_passed=n_passed, pass_all=pass_all, shortest_all=shortest_all, fatal=fatal,
                fails=fails, reads=reads, secs=round(time.time() - t0, 2),
                n_strict=n_strict, strict_all=(n_strict == n))


def strip_comments(code):
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type != tokenize.COMMENT:
                out.append(tok)
        return tokenize.untokenize(out)
    except Exception:
        return re.sub(r"#.*", "", code)


def normalise(code):
    """Comments, docstrings and whitespace removed. Used to find identical programs."""
    if not code:
        return ""
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module, ast.AsyncFunctionDef)):
                b = node.body
                if b and isinstance(b[0], ast.Expr) and isinstance(getattr(b[0], "value", None), ast.Constant) \
                        and isinstance(b[0].value.value, str):
                    node.body = b[1:] or [ast.Pass()]
        return ast.unparse(tree)
    except Exception:
        return re.sub(r"\s+", " ", strip_comments(code)).strip()


def code_hash(code):
    return hashlib.sha1(normalise(code).encode()).hexdigest()[:12]


def static_flags(code):
    c = strip_comments(code or "")
    f = dict(uses_heap=False, uses_fifo=False, uses_stack_pop=False, is_recursive=False,
             has_two_frontiers=False, uses_random=False)
    if not c.strip():
        return f
    f["uses_heap"] = bool(re.search(r"\bheapq\b|\bheappush\b|\bheappop\b|PriorityQueue", c))
    f["uses_fifo"] = bool(re.search(r"\bdeque\b|\.popleft\(|\.pop\(\s*0\s*\)|\bQueue\(", c))
    f["uses_stack_pop"] = bool(re.search(r"\.pop\(\s*\)", c))
    f["uses_random"] = bool(re.search(r"\brandom\b", c))
    try:
        tree = ast.parse(c)
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef):
                for n in ast.walk(fn):
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fn.name:
                        f["is_recursive"] = True
        # two frontiers: >=2 distinct names bound to a deque(...) call / heap list seeded with goal,
        # or tell-tale names
        dq = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
                fname = getattr(n.value.func, "id", getattr(n.value.func, "attr", ""))
                if fname == "deque":
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            dq.add(t.id)
        names = {n.id.lower() for n in ast.walk(tree) if isinstance(n, ast.Name)}
        tell = any(re.search(r"backward|bidir|_goal$|^goal_(queue|visited|front|parent|q)|(queue|visited|front|parent|q)_(b|g|end|goal|back)$|from_goal", x)
                   for x in names)
        f["has_two_frontiers"] = len(dq) >= 2 or tell
    except Exception:
        pass
    return f


FLAG_ORDER = ["uses_heap", "uses_fifo", "uses_stack_pop", "is_recursive", "has_two_frontiers", "uses_random"]


def signature(code, res=None):
    """(pass_all, shortest_all, uses_heap, uses_fifo, uses_stack_pop, is_recursive, has_two_frontiers, uses_random)"""
    if res is None:
        res = run_tests(code)
    f = static_flags(code)
    return tuple([bool(res["pass_all"]), bool(res["shortest_all"])] + [f[k] for k in FLAG_ORDER])


def sig_str(sig):
    return "".join("1" if x else "0" for x in sig)


def evaluate(text):
    """text -> dict with code, tests, signature (the row fields every stage stores)."""
    code = extract_code(text)
    res = run_tests(code)
    sig = signature(code, res)
    return dict(code=code, n_passed=res["n_passed"], pass_all=res["pass_all"], shortest_all=res["shortest_all"],
                n_strict=res["n_strict"], strict_all=res["strict_all"],
                fatal=res["fatal"], fails=res["fails"], sig=sig_str(sig),
                chash=code_hash(code) if code else None)


if __name__ == "__main__":
    refdir = os.path.join(os.path.dirname(ROOT), "round-1/experiment-1/src/tasks/t1_grid/references")
    for fn in sorted(os.listdir(refdir)):
        code = open(os.path.join(refdir, fn)).read()
        r = run_tests(code, count_reads=True)
        print(f"{fn:28s} n={r['n_passed']} all={r['pass_all']} shortest={r['shortest_all']} reads={r['reads']} "
              f"sig={sig_str(signature(code, r))} {r['secs']}s {r['fails'][:2]}")
    bad = "def solve(grid, start, goal):\n    while True: pass\n"
    print("loop", run_tests(bad))
    print("bomb", run_tests("def solve(g,s,t):\n    x=[0]*(10**10)\n    return []\n"))
    print("none", run_tests("x=1"))
