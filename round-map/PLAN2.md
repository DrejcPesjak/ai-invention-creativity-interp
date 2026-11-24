# round-map, part 2: take the five measurements apart

A plan for an agent starting with zero context. Read all of it, then `PLAN.md` (part 1) and `README.md` (its results), before doing anything. **Nothing here has been run.**

## 1. Why a second part

Part 1 gave every method one verdict, KNOWN or UNKNOWN, from one number: how many of 10 programs written from the method's name were judged to be that method and passed the tests. That number mixes five different things:

| # | Ability | The question | How part 1 handled it |
|---|---|---|---|
| 1 | **Recall** | Does the name bring up the right procedure at all? | Mixed with 3 in the "by name" count. |
| 2 | **Description** | Can the model state the procedure correctly in words? | Never asked. |
| 3 | **Coding** | Given the procedure, can it write a correct program? | Mixed with 1. The pseudo-code hint level measured it, but was reported as a "hint", not as coding. |
| 4 | **Preference** | Which method does it pick when it is free to choose? | Stage A and the "X is one well-known approach; implement any" hint. The second was counted as knowledge. |
| 5 | **Self-correction** | Given feedback, can it fix or change a program? | Mixed with 4 in the two loops. The model was never handed a failing program. |

Consequences seen in part 1:

- Bidirectional search was called "unknown". By name it was attempted 9 of 10 times and failed the tests every time, also from pseudo-code. That is recall without coding, not ignorance.
- "Does not know DFS" comes from a labelling split: recursion that carries the path is labelled X1 (backtracking), not DFS. Most people call both DFS.
- Random walk, wall follower and dead-end filling cannot solve the task. Refusing to write them is as much good sense as ignorance, yet they counted in "knows 6 of 14".
- The first-letter hint gave 1 right answer in 130 and has collisions (D = DFS, Dijkstra, dead-end filling). It measures nothing.
- The list prompt asked for "every" method; all 10 answers stopped at exactly 10 lines.
- The tree only opened positions where the tuned model was below 0.90. It is above that almost everywhere, including where BFS and DFS part (`pop(0)` vs `pop()`), so the base model never got to propose an alternative there.
- Thinking was off for every run.

Part 2 measures the five abilities separately, re-reads the part 1 data under the corrected grouping, and runs two checks on part 1's limits (thinking, tree entry rule).

## 2. Hard rules

Same as part 1, repeated because they are binding:

- **No git commits, no pushes, no `git pull`/`fetch`.** The owner commits by hand.
- **Write only inside `round-map/`.** Every other folder in the repo is read-only.
- **Python:** `/home/drew99/venvs/ml/bin/python`. Do not create another venv. A missing package is installed with `uv pip install --python /home/drew99/venvs/ml/bin/python <pkg>` and listed in the README.
- **Hardware:** one RTX 3070 Laptop, 8 GB VRAM.
- **Generated code is untrusted.** Run it only through `src/tools.py` `run_tests` (child process, `python -I -S`, time and memory limits). Never `exec` it in your own process.
- **Do not send repo content or user details to external services.**
- **Report honestly.** Failed stages and ugly numbers go in the README as they are.

Added for part 2:

- **Do not modify or delete part 1 files** (`README.md`, `results/`, `prompts/`, `logs/`, existing files in `src/`). Part 2 reads them and writes elsewhere. New code goes in new files under `src/`; importing `tools`, `gen`, `catalogue` is expected. If one of those three needs a change, add an optional argument that leaves the default behaviour identical, and say so in the README.
- **Write prompts and scoring checklists to disk before the stage that uses them runs.**

## 3. Fixed settings (carried over, do not re-decide)

- Models: `Qwen/Qwen3-4B` (tuned) and `Qwen/Qwen3-4B-Base` (stage T only). Precision is `bf16off` from `results/model_config.json`: bf16 with part of the model on the CPU, about 0.44 s per generated token step regardless of batch size. 8-bit is not to be used (its probabilities change with batch shape).
- Sampling: `temperature=1.0, top_p=0.95`, one seed per stage, recorded.
- Thinking is **off** everywhere except stage K.
- Pass rule: the 46 core tests (`tools.CORE`); strict 48 is recorded beside it.
- Method names in prompts are the exact names part 1 used (`src/catalogue.py`), so results join.
- Batch: 12 for 700-token answers; use `gen.safe_generate`, which halves the batch on out-of-memory.

Layout:

```
round-map/
  PLAN2.md           this file
  v2/
    README.md        the results (section 8)
    prompts/         every prompt, plus checklists.json
    refs/            the 14 reference programs used in stage N
    results/
    logs/progress.md
  src/               new files only (v2_*.py)
```

## 4. Method groups

Part 1's 14 rows stay, but are grouped:

| Group | Methods | Counted in "of N" summaries? |
|---|---|---|
| Can pass | BFS, DFS, BIDIR, ASTAR, GREEDY, DIJK, WAVE, RELAX | yes |
| Correct but too slow here | IDDFS, X1 (recursive backtracking), X2 (Floyd-Warshall) | yes; coding is scored on the judge's `faithful` flag, as in part 1 |
| Probes: cannot solve the task | DEADEND, WALL, RANDOM | **no**; reported in their own table as "will it write a method it would never choose" |

DFS and X1 are each reported twice: **strict** (part 1's labels) and **family** (labels DFS and X1 count as the same method).

## 5. Stages

Order is the run order. After each stage: write its `.jsonl`, read a few raw outputs, add two lines to `v2/logs/progress.md`.

### Stage R. Re-read part 1 (no GPU)

From `results/joined.jsonl` and `results/labels.jsonl`, with no new generation, compute per method:

- **Recall (to code), by name** = (RIGHT + BROKEN) of 10 in part 1 stage C: the model attempted the right method, working or not.
- **Coding given recall** = RIGHT of (RIGHT + BROKEN) in stage C. State the denominator; it is often small.
- **Coding from pseudo-code** = RIGHT of 10 at part 1 hint level H5.
- **Preference** = share unprompted (stage A, of 50) and share when the method is merely mentioned (hint level H2, of 10).
- DFS and X1 in strict and family versions.
- The first-letter level (H1) is dropped from every table.

Output `v2/results/R_regroup.json`. This is the baseline table the later stages fill in.

### Stage S. Describe (ability 2)

Prompt, no task statement, no code allowed:

> Do not write code. Explain step by step how {name} finds a path between two cells in a grid of free cells and walls, where a move goes to one of the 4 neighbouring cells.

14 methods × **10 samples**, `max_new_tokens=350`.

Scoring, by blind sub-agent judges (5.9), two questions per answer:

1. **Blind label.** The judge sees the answer with the method name masked (`{name}`, its abbreviation and obvious synonyms replaced by `[METHOD]`; do the masking by script and spot-check 20). The judge picks the catalogue method the text describes, or OTHER / VAGUE.
2. **Checklist.** The judge then gets the target's checklist below and marks each fact present / absent / contradicted.

Outcome per answer: **DESCRIBED** (blind label is the target, every required fact present, none contradicted), **PARTIAL** (blind label is the target, a fact missing), **OTHER-METHOD** (describes a different method; record which), **VAGUE**.

Checklists (required facts; save as `v2/prompts/checklists.json` before running):

| Method | Required facts |
|---|---|
| BFS | first-in-first-out frontier; cells explored in order of distance from the start; visited cells not re-entered; path recovered from predecessors or carried paths |
| DFS | follows one neighbour as deep as possible before trying others; stack or recursion; steps back when stuck; a visited record prevents re-entering cells |
| X1 | extends the current path one cell at a time; on a dead end undoes the last step; only the current path blocks revisits |
| IDDFS | depth-limited depth-first search; repeated with a growing limit; each round starts again from the start |
| BIDIR | one search from the start and one from the goal; they advance in turns or together; stop when a cell is reached by both; path joined from the two halves |
| ASTAR | priority queue; priority is steps so far plus an estimate to the goal; names a valid estimate (e.g. Manhattan distance) |
| GREEDY | priority queue; priority is the estimate to the goal only; steps so far are not part of the priority |
| DIJK | priority queue ordered by distance from the start; a cell's distance is lowered when a shorter way is found; no goal estimate |
| WAVE | distance numbers spread outward from the goal (or start), +1 per step; the path is read off by stepping to a neighbour whose number is one lower |
| RELAX | repeated passes over all cells (or all edges); a cell's distance is lowered from its neighbours; stops when a pass changes nothing (or after a fixed number of passes) |
| X2 | distance table for all pairs of cells; triple loop over an intermediate cell with `d[i][j] = min(d[i][j], d[i][k] + d[k][j])` |
| DEADEND | finds free cells with at most one free neighbour, except start and goal; fills them and repeats until none is left; what remains is the route |
| WALL | keeps one hand on a wall; state is position and facing direction; tries turns in a fixed order relative to the facing |
| RANDOM | steps to a randomly chosen free neighbour; repeats until the goal is reached; keeps no systematic record |

### Stage N. Recognise (ability 1, in the other direction)

Show a program, ask for the name.

- Build `v2/refs/{ID}.py`, one clean reference per method. Start from `round-1/experiment-1/src/tasks/t1_grid/references/` (read-only) and `src/pseudo_refs/`; write the missing ones. Each must pass the core tests through `run_tests`, except the "too slow" and probe methods, which must be faithful and pass what they can (record `n_passed`).
- Make a second, **neutral** copy of each: comments and docstrings removed, identifiers renamed so none hints at the method (`queue` → `a`, `heap` → `b`, `visited` → `c`, ...). Keep `import heapq` / `deque` (they are part of the code). Re-test the neutral copies.
- Prompt: the neutral program, then: *"Which path-finding algorithm does this function implement? Answer with the name only."* 14 × **10 samples**, `max_new_tokens=30`.
- Score by script plus eye: answer maps to the target, to another catalogue method (record which), or to nothing. For DFS/X1 report strict and family.

### Stage L. Longer lists (ability 1, free recall)

A three-turn conversation, **10 chains**:

1. `{SPEC}` + *"Do not write code. List as many different algorithms or approaches that could solve this task as you can, at least 30, one per line, with a one-sentence description."* (`max_new_tokens=1500`)
2. *"List more approaches that are not in your list above."*
3. The same again.

Map every item to a catalogue id, a **real other** method (name it), or **invented / not applicable** (e.g. part 1's "Welsh-Powell"). Report per catalogue method: lists containing it and the turn where it first appears; plus the count of real-other and invented items per turn. Real-other methods are reported, not carried into other stages.

### Stage P. Coding (ability 3)

Two sources of the procedure, both without the method name:

- **P1, from our pseudo-code.** Already run in part 1 for 13 methods (hint level H5). Run the missing one: BFS, **10 samples**, with BFS pseudo-code written in the same style as `src/catalogue.py` `PSEUDO`.
- **P2, from its own description.** For each stage S answer that scored DESCRIBED or PARTIAL (up to 10 per method), a two-turn conversation: turn 1 is the stage S prompt and that answer as the assistant message; turn 2 is `{SPEC}` + *"Implement the task using exactly the approach you just described."* One sample per answer.

Outcomes as in part 1: RIGHT / BROKEN / SWAPPED / JUNK against the target. P2's denominator is the number of usable descriptions; state it.

### Stage F. Repair (ability 5)

The model is handed a failing program and the failing test.

- **Pool:** from part 1's `results/joined.jsonl`, every distinct program that (a) fails the core tests, (b) is labelled as one of the eight "can pass" methods. Take at most 12 per method, chosen with a fixed seed. Expect about 30–60 programs, most of them bidirectional; report the pool per method. (Programs of the "too slow" and probe methods are excluded: they cannot be repaired into passing.)
- `run_tests` already records failing cases; make sure the record holds, for the first failing case: grid, start, goal, what was returned or which error or "timed out", and what was expected ("a valid path" or "[]"). Grids above 12×12 are shown as their size plus the first 12 rows; prefer the smallest failing case.
- **Arm T (with the test), up to 3 rounds per program:** `{SPEC}`, the program, then *"This program fails this test: {case}. It returned {got}; expected {expected}. Fix the program. Keep the same approach."* If the answer still fails, send the new first failing case in the same conversation. Stop at a pass or after round 3.
- **Arm N (no test), 1 round:** same, but the feedback is only *"This program is wrong on some inputs. Fix it. Keep the same approach."* This shows whether the test content is used at all.
- One sample per program per arm.

Outcome per program and arm: **FIXED-SAME** (passes, judged the same method), **FIXED-SWITCHED** (passes, different method; record which), **UNCHANGED** (identical after `tools.normalise`), **STILL-BROKEN**. For arm T also the round of the fix.

The part 1 scoring loop (F2) and rejection chains (F3) are not rerun. In the write-up they are filed under preference and steerability, not self-correction.

### Stage K. Thinking on (check on a part 1 limit)

Same prompts as part 1 stage A and stage C, with `enable_thinking=True`.

- **Pilot first:** 4 samples of stage A and 4 of "Implement this task using bidirectional search", `max_new_tokens=4096`. Record thinking length (tokens before `</think>`), total time, peak VRAM, and how many finished. **Gate:** if fewer than 6 of 8 finish inside 4096 tokens, or a batch of 8 takes more than 40 minutes, stop and report to the owner before the full run.
- **Full run:** stage A × 20 samples, stage C × 10 samples for all 14 methods. Budget = pilot's 90th-percentile length + 800, capped at 4096. Batch 8 or what fits.
- Store thinking text and answer separately. The program is extracted from the text after `</think>` only. No `</think>` inside the budget → outcome **CUT** (reported in its own column, not as JUNK).
- Also record, by script, which catalogue method names occur in the thinking text; it shows what was considered before the choice.
- Scoring identical to part 1 stage C, so the two columns compare directly.

### Stage T. Tree with a different entry rule (check on a part 1 limit)

Same procedure and constants as part 1 stage D (`src/stageD.py`), with two changes. Copy the file to `src/v2_stageT.py`; do not edit the original.

1. **Which positions open.** Part 1 opened a position when the tuned model's top-1 probability was below 0.90. Now: run the base model once over the whole tuned greedy answer (one forward pass gives the next-token distribution at every position), and open a position when **either** the tuned top-1 is below 0.90 **or** the base model's top-1 token differs from the tuned top-1.
2. **Which positions first.** There will be many (base and tuned differ on whitespace all the time). Rank positions by `1 − p_base(tuned top-1)`, highest first, take at most `MAX_POINTS=40` per path, and process them in text order.

Candidates at a position: base top-K tokens with probability ≥ `MIN_P`, plus the tuned top-1, plus the tuned second token if its probability is ≥ 0.01. `K=3, R=4, MAX_FORKS=3, MAX_ROLLOUTS=800` (stop when used up and say so).

Report as in part 1, plus: how many positions the new rule opened that the old one would not have, and whether the `pop(0)` / `pop()` position was among them. A tree that again shows only BFS is a valid result; report it as such.

### Stage X. More samples for the cells that carry a verdict (optional, last)

Every part 1 cell is 10 samples. If time remains, add 10 more to part 1 stage C and to hint level H5 for the 11 counted methods (new ids, new seed, same prompts), judged with everything else. Report 10-sample and 20-sample numbers side by side.

### 5.9 Judging

As in part 1 stage G, after all generation is finished:

- One shuffled sheet of every new **program** (stages P, F, K, T, X) without stage or prompt; judged by blind sub-agents with `results/judge/INSTRUCTIONS.md` unchanged (the DFS/X1 split is kept in the labels and merged only at report time). Programs already labelled in part 1 (same `tools.code_hash`) keep their label.
- A separate shuffled sheet for stage S **descriptions**, with its own instruction file written before judging (blind label first, then checklist).
- At least 10% of each sheet goes to two judges. Report agreement. You read every disagreement and at least 20 other items, and record changes in an adjudication file.
- Judges get the sheet chunk and the instruction file only.

## 6. Size and time

At about 0.44 s per token step, independent of batch size:

| Stage | Generations | Rough GPU time |
|---|---|---|
| R re-read | 0 | none |
| S describe | 140 short | 30–45 min |
| N recognise | 140 very short | 15 min |
| L longer lists | 30 turns | 30–40 min |
| P coding | 10 + up to 140 | 1–1.5 h |
| F repair | about 100–250 | 1.5–3 h |
| K thinking on | 8 pilot + 160 | 4–6 h |
| T tree | up to 800 rollouts | 3–5 h |
| X more samples (optional) | 220 | 1.5–2 h |

Run in the order of the table. S, N, L and P are cheap and settle "knows vs can code". K is the most likely to change the headline. T is the most expensive and the least certain to show anything new. If time runs short, cut X, then T, then halve K's stage C samples; record every cut.

## 7. What would change the part 1 conclusions

Written down before running, so the results cannot pick their own reading:

- A method **described** correctly in most answers but rarely RIGHT by name → it is known, and the failure is coding (ability 3) or name-to-code recall (ability 1), which P1/P2 tell apart.
- A method RIGHT from pseudo-code but OTHER-METHOD when described → it can follow instructions for it and does not know it.
- **Recognised** but not produced → the name is attached to the method on the reading side only.
- Thinking on moves a method from SWAPPED to RIGHT → part 1's "unknown" for it was a single-pass limit, not missing knowledge.
- Repair: FIXED in arm T well above arm N → the model uses test feedback. Equal rates → it is re-rolling, not correcting.
- Tree: a non-BFS branch with base mass above 0.03 → the default is a tuning effect at that position. None → the default is settled before any position the base model would contest.

## 8. What to deliver: `round-map/v2/README.md`

Short, plain, tables first, readable without this plan.

1. Three lines: what part 2 is, what was run, what was cut.
2. **The five abilities, one row per counted method** (11 rows; DFS and X1 with strict / family):

| Method | Listed: first turn it appears (of 10 chains) | Recognised (of 10) | Described (DESCRIBED / PARTIAL / OTHER-METHOD / VAGUE) | Recall by name: attempted (of 10) | Coding: from name / from pseudo-code / from own description | Preference: unprompted (of 50) / when mentioned (of 10) | Repair: with test / without (of pool) | By name with thinking (RIGHT / BROKEN / SWAPPED / CUT) |
|---|---|---|---|---|---|---|---|---|

3. The same table for the three probe methods, separately.
4. **One line per method** saying which of the five abilities it has, in words (e.g. "bidirectional: recalled and described, cannot code it, not repaired").
5. **Repair**: outcome counts per arm, and the round of the fix.
6. **Thinking**: thinking length, the part 1 vs thinking-on columns side by side, methods named in the thinking.
7. **Tree**: positions opened under the old and the new rule, forks, where each branch leads.
8. **What changed against part 1's README**: every part 1 claim that part 2 overturns, weakens or confirms, one line each.
9. **Problems**: what failed, judge agreement and counts of unsure labels, anything that looks wrong. Cells are 10 samples; say which differences are inside the noise.
10. How to re-run each stage (one command each).

End the final message with the same summary in a few lines. Do not commit.
