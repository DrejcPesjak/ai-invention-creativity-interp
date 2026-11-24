# round-map: what one small model knows about grid path-finding, and whether it can be pushed past that

## 1. In three lines

- **Model:** `Qwen/Qwen3-4B` (thinking off) writes everything; `Qwen/Qwen3-4B-Base` only proposes branch tokens for the tree. Both in true bf16, with about a quarter of the layers on the CPU because the model does not fit on the 8 GB card. T=1.0, top-p 0.95, 700 new tokens.
- **Task:** `solve(grid, start, goal)` returning any valid 4-neighbour path (`task/spec.txt`, 48 tests in `task/tests.json`).
- **Run:** every stage of `PLAN.md` (0, A–G), 1,022 generations, no sample count cut. Three deviations, all explained in section 6: a pass means the **46 core tests**, not 48; **8-bit was dropped** after it was found to be numerically unstable; the tree closed by itself after 76 of its 800 allowed rollouts.

**Short answer.** Unprompted the model writes BFS 50 times out of 50. It can write six of the fourteen methods when given the name. The only method it produced without being able to produce it by name is plain DFS, and that one is not new to it: it lists DFS every time and writes it under other names. Nothing else left the map. A scoring loop made it copy its input; rejecting repeats got it to DFS, A* and Dijkstra, all inside the map.

## 2. The map

A pass is 46/46 core tests. RIGHT = judged to be the asked method and passes; for methods that cannot pass in a pure form (marked †) a faithful implementation counts as RIGHT. KNOWN = at least 3 of 10 RIGHT by name.

| Method | Listed (of 10) | Unprompted (of 50) | In the tree? (prob. tuned / base) | By name (RIGHT / BROKEN / SWAPPED / JUNK) | KNOWN? | Lowest hint level | F1 problem change (RIGHT of 10) | F2 loop | F3 rejection (chains of 5 where accepted) |
|---|---|---|---|---|---|---|---|---|---|
| BFS | 10 | 50 | yes, the trunk (0.994 / 0.55) | 9 / 1 / 0 / 0 | yes | H0 (default) | – | 64 of 64 programs | 5 |
| DFS | 10 | 0 | only inside a failing branch (2 of 4 rollouts after ` visited`, 0.006 / 0.35) | 1 / 0 / 9 / 0 | **no** | never | **7** | 0 | **3** |
| IDDFS † | 3 | 0 | no | 7 / 3 / 0 / 0 | yes (too slow to pass) | H3 | 0 | 0 | 0 (1 broken attempt) |
| BIDIR | 8 | 0 | no | 0 / 9 / 1 / 0 | no | never | 0 | 0 | 0 (1 broken attempt) |
| ASTAR | 10 | 0 | no | 5 / 1 / 4 / 0 | yes | H3 | 0 | 0 | 2 |
| GREEDY | 6 | 0 | no | 1 / 0 / 9 / 0 | no | H4 | 0 | 0 | 0 |
| DIJK | 10 | 0 | no | 9 / 1 / 0 / 0 | yes | H3 | 0 | 0 | 1 |
| WAVE | 0 | 0 | no | 0 / 0 / 10 / 0 | no | H4 | 0 | 0 | 0 |
| RELAX | 0 | 0 | no | 6 / 1 / 3 / 0 | yes | H3 | 0 | 0 | 0 |
| DEADEND † | 0 | 0 | no | 0 / 0 / 10 / 0 | no | H5 | 0 | 0 | 0 |
| WALL † | 1 | 0 | no | 0 / 5 / 5 / 0 | no | H5 | 0 (1 broken) | 0 | 0 |
| RANDOM † | 1 | 0 | no | 0 / 0 / 10 / 0 | no | H5 | 0 | 0 | 0 |
| X1 recursive backtracking † (extra) | 10 | 0 | no | 6 / 2 / 1 / 1 | yes | H3 | not run | 0 | 0 (failing attempts in all 5) |
| X2 Floyd-Warshall † (extra) | 1 | 0 | no | 0 / 0 / 10 / 0 | no | never | not run | 0 | 0 |

### The hint ladder in full (RIGHT of 10 at each level)

H1 = first letter of the name, H2 = name mentioned in passing, H3 = "implement using {name}", H4 = one-sentence mechanism without the name, H5 = pseudo-code without the name. The threshold is 5 of 10.

| Method | H0 (of 50) | H1 | H2 | H3 | H4 | H5 |
|---|---|---|---|---|---|---|
| DFS | 0 | 0 | 4 | 1 | 1 | 0 |
| IDDFS † | 0 | 0 | 2 | 7 | 5 | 6 |
| BIDIR | 0 | 0 | 0 | 0 | 0 | 0 |
| ASTAR | 0 | 1 | 2 | 5 | 6 | 5 |
| GREEDY | 0 | 0 | 3 | 1 | 10 | 7 |
| DIJK | 0 | 0 | 0 | 9 | 10 | 10 |
| WAVE | 0 | 0 | 0 | 0 | 8 | 7 |
| RELAX | 0 | 0 | 0 | 6 | 1 | 10 |
| DEADEND † | 0 | 0 | 0 | 0 | 1 | 5 |
| WALL † | 0 | 0 | 0 | 0 | 0 | 5 |
| RANDOM † | 0 | 0 | 0 | 0 | 0 | 8 |
| X1 † | 0 | 0 | 2 | 6 | 4 | 10 |
| X2 † | 0 | 0 | 0 | 0 | 0 | 4 |

### What it writes instead (by name, the SWAPPED column)

| Asked for | What came out |
|---|---|
| depth-first search | 9 × recursive backtracking (X1: `not in path`, path copied at each call), most with a bug |
| greedy best-first search | 9 × Dijkstra (heap keyed by path length; the goal estimate is never used) |
| the wavefront (Lee) algorithm | 10 × BFS |
| dead-end filling | 5 × BFS, 5 × backtracking |
| a random walk | 5 × DFS, 4 × BFS, 1 × backtracking (some shuffle the neighbour order) |
| the wall follower algorithm | 5 broken wall followers, 3 × "go straight, else rotate" walkers, 2 × DFS |
| A* search | 5 right; 2 × Dijkstra; 2 × heap whose key adds up the heuristic along the path (see section 5) |
| the Floyd-Warshall algorithm | 6 × sweep relaxation called "Floyd-Warshall", 2 × BFS, 2 × other |
| sweep relaxation | 6 right; 2 × BFS, 1 × Dijkstra |

Things worth noticing in the map:

- **Listing is not knowing, in both directions.** Bidirectional search is in 8 of 10 lists and was never written correctly at any level, pseudo-code included (0 of 60). Sweep relaxation is in no list and is written correctly from its name 6 times out of 10.
- **The name "DFS" points at the wrong code.** Asked for DFS, the model writes path-copying backtracking. Given DFS as pseudo-code (H5) it still turned it into backtracking in 9 of 10 answers, adding an un-mark step that the pseudo-code does not have and dropping the goal test.
- **"Greedy best-first" is Dijkstra to this model** until the mechanism is spelled out (H4: 10 of 10).
- **The first-letter hint (H1) does nothing** (1 RIGHT in 130) and makes answers worse than no hint: pass rate drops from 50/50 to about 55%.
- Strict 48/48: the two extra cases (start equals goal on a wall) pass in 102 of 1,012 programs. The model almost always tests `start == goal` before testing for a wall.

## 3. The tree

Greedy answer of the tuned model: 254 tokens, a BFS that passes. Hesitation points (tuned top-1 below 0.90): **5**. Wording only: **4**. Real forks: **1**. One prefix was opened to a second level: 3 more hesitation points, all wording. 76 rollouts used of 800; the tree was not cut, it ran out of forks.

```
(root)  prompt = SPEC                                              tuned 1.0   / base 1.0
│
├─ token 36  after "cols = len(grid[0"      `])` vs `])\n`         wording  (all 8 rollouts: BFS, pass)
├─ token 47  after "... if rows > 0 else 0\n   "                   REAL FORK
│    ├─ ` directions` (tuned 0.59, base 0.24)  trunk               4/4 BFS, pass
│    ├─ ` if`         (tuned 0.40, base 0.19)  same as trunk       4/4 BFS, pass
│    ├─ ` visited`    (tuned 0.006, base 0.35)  rollouts disagree  2 BFS + 2 DFS, 0/4 pass
│    │     └─ opened as level 1; its greedy answer is a BFS that fails tests
│    │          ├─ token 65  `])]\n` / `])` / `[`                  wording  (12 rollouts: BFS, 0 pass)
│    │          ├─ token 66  `    \n` / `   `                      wording  (8 rollouts: BFS, 0 pass)
│    │          └─ token 69  ` [` / ` [(`                          wording  (8 rollouts: BFS, 0 pass)
│    │          LEAF  BFS, failing                                 tuned 0.0058 / base 0.35
│    └─ ` queue`      (tuned 0.000004, base 0.10)                  LEAF  4/4 BFS, 0/4 pass
├─ token 49  after "directions ="           ` [(` vs ` [`          wording  (BFS, pass)
├─ token 72  after "(-1, 0"                 `)]` vs `)]\n`         wording  (BFS, pass)
└─ token 134 after "[start])]\n"            `    \n` vs `   `      wording  (BFS, pass)
LEAF  greedy trunk: BFS, passes                                    tuned 0.994 / base 0.55
```

| Leaf | Fork position | Forced token | Judged method | Rollouts passing | Prob. tuned | Prob. base |
|---|---|---|---|---|---|---|
| trunk | – | – | BFS | greedy passes; 40 of 40 rollouts along it pass | 0.994 | 0.55 |
| ` visited` | 47 | ` visited` | BFS that fails (2 of the 4 first rollouts are failing DFS) | 0 of 33 | 0.0058 | 0.35 |
| ` queue` | 47 | ` queue` | BFS that fails | 0 of 4 | 0.000004 | 0.10 |

Reading: the base model would start the body with `visited` or `queue` 45% of the time; the tuned model does so 0.6% of the time. Those base-preferred openings do not lead to another method. They lead to the same BFS written in an order the tuned model then gets wrong. The tree contains one working method.

## 4. Did it get outside its map?

**One method, with a caveat: DFS.**

DFS is UNKNOWN by the plan's rule (1 of 10 RIGHT by name) and never reaches 5 of 10 at any hint level. It came out RIGHT in two of the three push stages:

- **F1, problem change** ("No imports and no queue-like containers are allowed; extra memory must stay proportional to the length of the path"): 7 of 10 are correct DFS with a permanent visited set. The other 3 are failing backtracking.
- **F3, reject repeats:** a passing DFS was accepted in 3 of 5 chains (step 5 or 6, after one or two rejected attempts).
- F2, scoring loop: nothing.

The caveat is that this is a wrong address, not a new idea. The same DFS appears, passing, when the model is asked for other things: "a random walk" by name (5 of 10), the random-walk mechanism sentence (8 of 10), and the F1 requirements written for RANDOM (4), RELAX (3) and DEADEND (2). The model owns DFS; the words "depth-first search" retrieve something else.

Example (F1, target DFS, sample 0; 46/46):

```python
def solve(grid, start, goal):
    if start == goal:
        return [start]
    rows = len(grid)
    cols = len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    visited = set()
    path = []

    def dfs(r, c, path):
        path.append((r, c))
        if (r, c) == goal:
            return True
        visited.add((r, c))
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        for dr, dc in directions:
            nr, nc = (r + dr, c + dc)
            if 0 <= nr < rows and 0 <= nc < cols and (grid[nr][nc] == '.') and ((nr, nc) not in visited):
                if dfs(nr, nc, path):
                    return True
        path.pop()
        return False
    if dfs(start[0], start[1], path):
        return path
    else:
        return []
```

**Everything else: none.** The methods first reached at H4 or H5 (GREEDY, WAVE, DEADEND, WALL, RANDOM) and the other UNKNOWN ones (BIDIR, X2) never came out RIGHT in F1, F2 or F3.

How the three pushes behaved:

- **F1.** The added requirement was ignored in 109 of 110 answers. The requirements for IDDFS, BIDIR, ASTAR and GREEDY each gave 10 of 10 plain BFS. Requirements that forbid the queue outright (DFS, RELAX, DEADEND, WALL, RANDOM) moved the model off BFS, but only to DFS or backtracking. Whether each sample respects its requirement:

| Target | Respects the requirement (of 10) | What was written |
|---|---|---|
| DFS | 0 (no imports and no queue: 10; memory proportional to the path: 0) | 7 DFS, 3 backtracking (fail) |
| IDDFS | 0 | 10 BFS |
| BIDIR | 0 | 10 BFS |
| ASTAR | 0 | 10 BFS (1 fails) |
| GREEDY | 0 | 10 BFS |
| DIJK | 0 | 8 BFS (3 with an unused `get_cost` stub), 2 backtracking |
| WAVE | 0 | 9 BFS, 1 backtracking |
| RELAX | 0 | 3 DFS, 3 BFS, 4 unusable |
| DEADEND | 0 | 4 backtracking, 5 DFS, 1 BFS; several try to write marks into the grid strings and crash |
| WALL | 1 (keeps only cell and direction; loops forever) | 4 DFS, 4 other walkers, 1 BFS, 1 broken wall follower |
| RANDOM | 0 | 6 DFS, 4 backtracking; `random` is imported only to shuffle neighbour order |

- **F2.** Score = average grid-cell reads over the tests. References for context: greedy best-first 176, A* 362, recursive DFS 445, bidirectional 462–535, stack DFS 571, BFS 660–686, Dijkstra 683–685, IDDFS about 41,000–44,000. The three seeds (best stage A programs) all score 658.4.

| Round | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| Best score | 658.4 | 658.4 | 658.4 | 658.4 | 658.4 | 658.4 | 658.4 | 658.4 | 658.4 |
| Valid new programs (of 8) | – | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 |

  All 64 programs pass, all are BFS, all score exactly 658.4. 57 of 64 are verbatim copies of a stage A program and there are 3 distinct programs in total. Every program that was ever in the top 3 is BFS. Asked to "write a different solve that reads fewer cells", the model returned what it was shown.

- **F3.** Judged method per step; `✓` accepted, `r` rejected as a repeat, `f` rejected for failing (tests passed of 46).

| Chain | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| 0 | BFS ✓ | X1 f(32) | BFS r | BIDIR f(13) | DFS ✓ | OTHER ✓ | BFS r | DFS f(11) |
| 1 | BFS ✓ | DFS f(11) | BFS r | IDDFS f(8) | DFS r | ASTAR ✓ | BFS r | DFS r |
| 2 | BFS ✓ | X1 f(32) | BFS r | BFS f(11) | X1 r | DFS ✓ | DIJK ✓ | DFS r |
| 3 | BFS ✓ | X1 f(11) | X1 r | X1 r | BFS f(36) | BFS r | ASTAR ✓ | X1 r |
| 4 | BFS ✓ | BFS r | X1 f(11) | BFS r | DFS ✓ | OTHER f(34) | X1 r | BFS r |

  Each chain got 2 or 3 accepted programs in 8 steps. In 11 of the 35 later steps the model wrote BFS again. The accepted set is BFS, DFS, A*, Dijkstra and one accumulated-heuristic heap: all in the lists of stage B.

## 5. OTHER pile (programs that pass all core tests)

10 distinct OTHER programs pass; they are two kinds.

| Kind | Programs | Where from | What it does |
|---|---|---|---|
| Accumulated-heuristic best-first | 9 (P0145, P0218, P0256, P0337, P0425, P0470, P0525, P0539, P0571) | asked for A* (by name 2, H1 2, H2 4) and once in F3 | A heap whose key is `parent's key + 1 + h(new cell)`: the goal estimate is added again at every step, so the key is neither steps + estimate (A*) nor the estimate alone (greedy). It is a failed A*, not a designed method; it passes because any path is accepted. |
| Distance fill by heap, then BFS downhill | 1 (P0328) | H4 for WAVE | Fills distances from the goal with a steps-only heap, then runs a FIFO BFS from the start that may only step to smaller numbers, with predecessor links. A mixture of Dijkstra, wavefront and BFS. |

The 19 other OTHER programs fail: recursion with no visited record at all (8), "go straight, rotate when blocked" walkers (3), two full BFS runs spliced wrongly (2), a "Floyd-Warshall" gate on a wrong table (3), and three one-offs.

## 6. Problems

**Changes to the plan**

- **Stop gate and the pass rule.** In stage 0 the model wrote BFS 10 of 10 times and failed the same two tests every time (start equals goal on a wall cell: it returns `[start]` before checking for a wall). Strictly that is 0 of 10 and the plan says stop. The owner chose to continue with a pass defined as the 46 other cases, and to record the strict result too (`n_strict`, `strict_all` in every row). Every number in this README uses the 46-case rule.
- **Precision.** bf16 on the GPU alone does not fit. 8-bit bitsandbytes loaded and stages 0–D were first run with it, but its next-token probabilities for the *same context* changed by up to 0.79 depending on the batch it was computed in, which makes the tree's probabilities meaningless (`results/precision_check_*.json`). 4-bit is stable but picks a different top token than bf16 at 3 of 8 hesitation points. The run was redone in bf16 with 10 of 40 modules on the CPU. This is at the plan's speed limit (about 2 minutes per batch), not under it; total generation time was about 7 hours. bf16 itself still moves by up to 0.047 between batch shapes. The 8-bit outputs are in `results/8bit_run/` and are not used.
- **IDDFS counted as a "cannot pass" method.** The catalogue says a pure IDDFS passes (slow). My own implementation of the H5 pseudo-code passes only 34 of 46 within the 2 s limit (`src/pseudo_refs/IDDFS.py`), so faithful IDDFS counts as RIGHT. Under the plan's literal rule IDDFS would be 0 RIGHT at every level and UNKNOWN. No IDDFS program passed all tests anywhere.
- **Two extra rows.** Stage B added X1 (recursive backtracking, in 10 of 10 lists) and X2 (Floyd-Warshall, 1 list). They went through stages C and E; no F1 requirement was written for them. "Welsh-Powell" / "Welsh-Park" appears in 5 of 10 lists; it is a graph-colouring algorithm (or nothing), so it was not carried.
- **Stage D details the plan left open.** The branch token of a group is the one most probable under the base model. The trunk's mass is the node mass times (1 − mass of the branches that left it). The tree used 76 rollouts; I did not spend the remaining budget on looser thresholds.
- **F2 and F3 wording.** F2 adds two sentences explaining the score before the plan's sentence. F3 says "of 46 pass".

**Judging**

- The blind sheet has 643 distinct programs (1,012 rows with code; identical programs merged). I did not read all of them myself: eight fresh sub-agents each labelled one shuffled chunk from `results/judge/INSTRUCTIONS.md`, seeing only code and test counts, never stage or prompt. Every program was read in full; the "read 3 per group" shortcut was not used.
- 40 programs were labelled twice by different judges: 39 of 40 agree on the label, 38 of 40 on label and faithfulness.
- I read about 20 programs myself (all cells that the conclusions rest on) and changed 13 labels (`results/judge/adjudication.jsonl`): 11 accumulated-heuristic heaps from "A*, not faithful" to OTHER, one "bidirectional" whose two fronts collapse into one from BIDIR to BFS, and one tie.
- Known soft spots, left as the judges wrote them: recursion with no visited record is DFS for some judges (3 programs) and OTHER for others (8), all failing; "go straight, else rotate" walkers are WALL-not-faithful (8) or OTHER (3), all failing; cut-off programs are JUNK (2) or the method they started (4). These move programs between BROKEN and SWAPPED only; none is RIGHT either way.
- 194 of 643 programs are marked not faithful. For † methods RIGHT depends on that single judge's "faithful" call.
- The F1 "respects the requirement" column was judged by me, not blind, from static checks over all 110 programs plus reading one or two per target.

**Things that look wrong or weak**

- Ten samples per cell. A cell of 4 versus 6 is not a difference; the 5-of-10 threshold for the hint level is sensitive to that (ASTAR 5, DEADEND 5, WALL 5 sit exactly on it).
- H1 uses the first letter of my prompt name; RELAX is "S" (sweep relaxation), and several letters are shared (D: DFS, Dijkstra, dead-end; B: BFS, bidirectional; W: wavefront, wall follower).
- The F2 score can be gamed (`in`, `join` and `find` on a row are not counted as reads). The model never tried.
- F2's three seeds all had the same score and near-identical code, so "top 3" showed the model three copies of one program.
- The F3 repeat test is the rough signature, which includes pass/fail. A failing variant of an already-accepted method therefore gets the "fails" message, not the "repeat" message.
- One model, one task, one sampling setting, 4-neighbour grids up to 30×30.

## 7. Re-running

Python is `/home/drew99/venvs/ml/bin/python`; no package was installed. Run from `round-map/`. Stages are resumable by sample id (delete the stage's `.jsonl` to start over).

| Stage | Command |
|---|---|
| tools self-test (references) | `python src/tools.py` |
| 0 smoke test, bf16 with offload | `python src/stage0.py bf16off` |
| A unprompted | `python src/stages.py A` |
| B lists | `python src/stages.py B` (then map by hand into `results/stageB_mapping.json`, extras into `results/extras.json`) |
| C by name | `python src/stages.py C` |
| D tree | `src/run_stageD.sh` |
| E hint ladder | `python src/stages.py E` |
| F1 problem change | `python src/stages.py F1` |
| F2 scoring loop | `python src/stageF2.py` |
| F3 reject repeats | `python src/stageF3.py` |
| G sheet | `python src/sheet.py` (then label the chunks in `results/judge/`) |
| G join and tables | `python src/report.py` |
| precision check | `python src/precision_check.py 8bit` (or `4bit`, `4bit32`, `bf16off`) |

Files: `results/stage*.jsonl` (raw outputs and test results), `results/judging_sheet.jsonl`, `results/labels.jsonl`, `results/joined.jsonl` (one row per sample with label and outcome), `results/summary.json` (every table above), `results/stageD_points.jsonl` and `stageD_leaves.jsonl`, `results/F1_requirement.json`, `prompts/` (every prompt), `logs/progress.md`.
