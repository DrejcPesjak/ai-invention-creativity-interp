# progress

## Stage 0 (smoke test) - GATE FIRED
- Precision: bf16 does not fit (OOM at load); 8-bit bitsandbytes loads (4.1 GB), 6.8 tokens/s per sequence, about 40 s per batch of 8 (answers are ~270 tokens). 8-bit kept.
- 10/10 answers are BFS and pass 46/48; all 10 fail the same two cases (`one_by_one_wall`, `start_equals_goal_wall`): the code returns `[start]` for start == goal before checking that the cell is a wall. 0/10 pass all tests, so the stop gate (fewer than 5 of 10) fired.
- Owner's decision: keep spec and tests, count a pass on the 46 core cases (without the two start==goal-on-wall cases), record strict 48/48 too. Core gate: 10/10. From here `n_passed` is out of 46 and `pass_all` means 46/46; `n_strict`/`strict_all` are the 48-case result.

## Stage A (unprompted, 50)
- 47/50 pass the 46 core cases, all 50 use a FIFO queue by signature (default looks like BFS; final label at judging). 1 of 50 also passes strict 48/48. 30 distinct programs.
- 3 failures: one recursive (11/46), two FIFO programs with 44-45/46.

## Stage B (lists, 10)
- Every list has BFS, DFS, Dijkstra, A*, and 'backtracking'. BIDIR 7, IDDFS 5, GREEDY 4, WALL 1. Never listed: WAVE, RELAX, DEADEND, RANDOM.
- Extra row X1 = recursive backtracking (10/10). 'Welsh-Powell' (3 lists) is a colouring algorithm, not carried. Mapping in results/stageB_mapping.json.

## Stage C (by name, 130)
- By signature only (labels come at judging): BFS, A*, greedy, Dijkstra 10/10 pass; "dead-end filling" gives 10/10 passing FIFO programs (looks like BFS under another name); DFS 2/10 pass, IDDFS 0/10, backtracking 0/10, bidirectional 1/10, wall follower 1/10.
- No answer without code, 1 hit the 700-token limit. 24 min for 130 samples.

## Precision change: 8-bit dropped, everything re-run in bf16 with CPU offload
- Found while checking stage D: in 8-bit bitsandbytes the next-token distribution of the *same context* changes with the batch it is computed in (probability differences up to 0.79 between a single forward and a padded batch; results/precision_check_8bit.json). The tree's probabilities would be meaningless. 4-bit nf4 is stable (max diff 0.018) but its top-1 token differs from the bf16 reference at 3 of 8 hesitation points. Reference bf16 itself: max diff 0.047.
- Chosen: true bf16 weights with `device_map=auto`, 5800 MiB on the GPU and the rest (10 of 40 modules) on the CPU ("bf16off"). 0.44 s per decoding step almost independent of batch size, so about 2 min per batch of 8-16. This is the plan's first choice (bf16) made to fit; it is at the plan's speed limit, not under it.
- All 8-bit outputs (stages 0, A, B, C, D) are kept in results/8bit_run/ and logs/8bit_run/ and are not used in the README tables. Stage 0 in bf16: 9/10 pass core-46 (1 syntax error), 0/10 strict.

## Stage A (bf16, 50)
- 50/50 pass the 46 core cases with the FIFO signature (BFS by signature); 3/50 also pass strict 48/48. 21 distinct programs.
- 8 min for 50 samples (batch 16).

## Stage B (bf16, 10 lists)
- All 10: BFS, DFS, Dijkstra, A*, backtracking. BIDIR 8, GREEDY 6, IDDFS 3, WALL 1, RANDOM 1. Never: WAVE, RELAX, DEADEND.
- Extras carried: X1 recursive backtracking (10/10), X2 Floyd-Warshall (1/10). 'Welsh-Powell'/'Welsh-Park' (5 lists) is a confabulation, not carried.

## Stage C (bf16, by name, 140 = 14 methods x 10)
- Pass core-46 by signature: GREEDY 10, WAVE 10 (all FIFO signature), BFS 9, A* 9, DIJK 9, RANDOM 9, RELAX 8, DEADEND 5, DFS 1, and 0 for BIDIR, IDDFS, WALL, X1 backtracking, X2 Floyd-Warshall. Labels come at judging.
- Read a few raw outputs: "DFS" answers are path-carrying recursion with real bugs (start duplicated in the path), not runner artefacts. 50 min; the first attempt died of out-of-memory at batch 16 (fallback fixed, batch now 12).

## Stage D (bf16, the tree)
- Greedy answer: 254 tokens, 5 hesitation points (top-1 < 0.90). 4 are wording only, 1 is a real fork (token 47, before `directions`): base-preferred tokens ` visited` (base 0.35, tuned 0.006) and ` queue` (base 0.10, tuned 4e-6) lead to programs that fail tests. One prefix was opened (level 1): 3 points, all wording. Tree closed after 2 levels, 76 of 800 rollouts used.
- Probabilities recorded during greedy decoding now agree with the recomputed ones (0.59 vs 0.589), unlike the 8-bit run.

## Stage E (hint ladder, 520) and F1 (problem change, 110)
- E: 3 h 50 min, 5 out-of-memory splits handled. F1: 34 min. No answer without code. By signature only: H5 pseudo-code gives all-pass for A*, Dijkstra, RELAX but 0/10 for DFS, IDDFS, DEADEND, WALL, backtracking.
- F1 by signature: the IDDFS, BIDIR, ASTAR, GREEDY requirements still give 9-10/10 FIFO (BFS-looking) programs.

## Stage F3 (reject repeats, 5 chains x 8) and F2 (scoring loop, 8 rounds x 8)
- F3: after the first BFS, most steps are rejected (fail or repeat); accepted new signatures appear in 4 of 5 chains (recursive, stack, heap).
- F2: first run died of out-of-memory (prompt with three programs, batch 8); re-run in half-batches. All 64 programs pass, all score exactly 658.4 = the score of the three seeds; 57 of 64 are verbatim copies of a stage A program, 3 distinct programs in total. The score never moved.

## Stage G (judging) and report
- Blind sheet: 643 distinct programs in 8 shuffled chunks, one fresh sub-agent judge per chunk, 40 programs judged twice (39/40 agree on the label). 13 labels changed by me after reading (results/judge/adjudication.jsonl).
- Checked my own H5 pseudo-code with hand implementations (src/pseudo_refs/): DFS, BIDIR, WAVE, RELAX pass 46/46; IDDFS passes 34/46 (timeouts), so faithful IDDFS counts as RIGHT. README written; every number in it re-checked against results/summary.json and results/joined.jsonl.
