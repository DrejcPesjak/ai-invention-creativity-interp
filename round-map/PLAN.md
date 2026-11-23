# round-map: what does a small model know about one task, and can it be pushed past that?

A plan for an agent starting with zero context. Read all of it before doing anything.

## 1. What this is

Ask a code LLM to "find a path through a grid" 100 times and it writes the same algorithm (BFS) about 100 times. Earlier work in this repo showed that. It did not answer two things:

1. **What does the model know?** Which path-finding methods can it produce, and how much help does each one need (none / a hint / the name / pseudo-code)?
2. **Can it reach a method it does not know?** If it cannot write method X even when given X's name, can it still arrive at X when the *problem* is changed so that X is the natural answer, or when a loop gives it feedback?

"Creativity" here means the local kind: producing something that is new *to this model*, not new to the world. So step one is a map of what the model knows, and step two tries to get it outside that map.

You will run one small model on one task on a laptop GPU, and **you are the judge**: you read the generated programs and say which method each one is.

## 2. Hard rules

- **No git commits, no pushes, no `git pull`/`fetch`.** The owner commits by hand.
- **Write only inside `round-map/`.** Every other folder in the repo is read-only for you.
- **Python:** use the existing uv venv, interpreter `/home/drew99/venvs/ml/bin/python` (Python 3.12, torch 2.12 + CUDA, transformers 5.14, accelerate, bitsandbytes, numpy, pandas, matplotlib are installed). Do not create another venv. If a package is missing, install with `uv pip install --python /home/drew99/venvs/ml/bin/python <pkg>` and list it in the README.
- **Hardware:** one RTX 3070 Laptop, 8 GB VRAM. Nothing else.
- **Generated code is untrusted.** Run it only in a separate process: `python3 -I -S`, time limit, memory limit (see 5.2). Never `exec` it in your own process.
- **Do not send repo content or user details to external services.** Downloading public model weights from Hugging Face is fine.
- **Library APIs may have changed** from what you remember (transformers 5.x). Check the installed version's behaviour with a tiny test before building on it.
- **Report honestly.** Failed stages and ugly numbers go in the README as they are.

## 3. Setup

### 3.1 Models

| Role | Model | Notes |
|---|---|---|
| tuned (writes everything) | `Qwen/Qwen3-4B` | chat template with `enable_thinking=False` |
| base (only proposes branch tokens in stage D) | `Qwen/Qwen3-4B-Base` | fed the *same token ids* as the tuned model (chat-template tokens included) |

- Both repo ids exist (checked by the owner). About 8 GB download each.
- **Load one model at a time, never both.** A 4B model in bf16 is about 7.7 GB of weights, so even one is a tight fit on this 8 GB card. In stage 0, try precisions in this order and keep the first that loads and generates a batch of 4 without running out of memory at a usable speed: (1) bf16, (2) 8-bit bitsandbytes, (3) 4-bit nf4. Use the same precision for both models and record it.
- Only stage D needs the base model, and it is written level by level (see there) so the models are swapped only a few times. Unload fully (`del`, `gc.collect()`, `torch.cuda.empty_cache()`) before loading the other.
- Fallback if Qwen cannot be downloaded: `google/gemma-3-4b-it` is already in the local HF cache. Record which model was used.

### 3.2 Sampling settings (everywhere unless stated)

`temperature=1.0, top_p=0.95, max_new_tokens=700`, batch as large as fits (try 8). Fix and record a seed per stage.

### 3.3 The task

Copy these two files into `round-map/task/` and use them unchanged:

- `round-1/experiment-1/src/tasks/t1_grid/spec.txt` — the task statement. This text is **SPEC** below.
- `round-1/experiment-1/src/tasks/t1_grid/tests.json` — 48 test cases: `{id, grid, start, goal, reachable, shortest_len}`.

In short: `solve(grid, start, goal)` returns any valid path as a list of `(row, col)` tuples, or `[]` if there is none. The path does not have to be shortest.

Reference implementations of six methods are in `round-1/experiment-1/src/tasks/t1_grid/references/` (read-only; useful to test your runner).

### 3.4 Folder layout to produce

```
round-map/
  PLAN.md            this file
  README.md          the results (section 8)
  task/              spec.txt, tests.json
  src/               your code
  prompts/           every prompt text, written BEFORE its stage runs
  results/           one .jsonl per stage + the judging sheet
  logs/
```

## 4. The catalogue

The reference list of methods. Everything is measured against it.

| Id | Method | One-sentence mechanism (used as the "description" hint) | Can a pure version pass all tests? |
|---|---|---|---|
| BFS | breadth-first search | Explore cells in rings of increasing distance from the start using a first-in-first-out queue, remembering each cell's predecessor. | yes |
| DFS | depth-first search | Keep going forward into an unvisited neighbour as far as possible and step back only when stuck (recursion or an explicit stack). | yes |
| IDDFS | iterative deepening DFS | Run a depth-limited forward search again and again, raising the depth limit by one each time. | yes (slow) |
| BIDIR | bidirectional search | Grow one search from the start and one from the goal in turns and stop when they touch, then join the two half-paths. | yes |
| ASTAR | A* | Always expand the cell with the smallest (steps so far + straight-line estimate to the goal), using a priority queue. | yes |
| GREEDY | greedy best-first | Always expand the cell that looks closest to the goal, ignoring steps so far, using a priority queue. | yes |
| DIJK | Dijkstra / uniform cost | Always expand the cell with the smallest steps-so-far using a priority queue of distances. | yes |
| WAVE | wavefront / Lee | First write into every reachable cell its distance from the goal, then walk from the start always stepping to a neighbour with a smaller number. | yes |
| RELAX | sweep relaxation (Bellman-Ford style) | With no queue at all, sweep over the whole grid repeatedly, lowering each cell's distance from its neighbours, until a sweep changes nothing. | yes |
| DEADEND | dead-end filling | Repeatedly turn free cells that have only one free neighbour (and are not start or goal) into walls, until none are left. | no (open areas remain) |
| WALL | wall follower | Keep one hand on the wall: store only position and facing direction, and always try to turn the same way first. | no |
| RANDOM | random walk | Step to a random free neighbour until the goal is reached. | no (time limit) |

Anything else a program does is **OTHER**, with a one-line description from you.

## 5. Tools to build first

### 5.1 `generate`

One function used by every stage: takes chat messages (and optionally a forced beginning of the answer), returns the text, the token ids and, when asked, per-step probabilities. Extract the program as the first ```python block containing `def solve`.

### 5.2 `run_tests`

Runs one program on the 48 cases in a subprocess (`python3 -I -S`, 2 s per case, 20 s total, 1 GB address-space limit, recursion limit raised and a big thread stack so recursive DFS is not unfairly killed). A case passes if:

- unreachable case (`reachable` false): returns `[]`
- otherwise: path starts at start, ends at goal, consecutive cells are 4-neighbours, all cells are free and inside the grid

Output per program: `n_passed` (of 48), `pass_all`, and `shortest_all` (true if every returned path has exactly `shortest_len` cells).

Check the runner on the six reference files: all must give `pass_all`.

### 5.3 `signature` (automatic, rough)

A cheap fingerprint used for grouping, **not** the final label:

`(pass_all, shortest_all, uses_heap, uses_fifo, uses_stack_pop, is_recursive, has_two_frontiers, uses_random)`

from simple checks on the code (`heapq`, `deque`/`popleft`/`pop(0)`, `.pop()`, a function calling itself, `random`) plus the test results.

### 5.4 The judge (you)

- Collect every program from every stage into `results/judging_sheet.jsonl` with: a random id, the code, `n_passed`, `shortest_all`. **Leave out which stage or prompt it came from**, and shuffle. Label from the sheet only, so the prompt cannot bias the label.
- For each program write: `label` (a catalogue id or OTHER), `note` (one line, required for OTHER), `names_used` (method names that appear in comments or identifiers).
- **Label what the code does, not what it says.** A program that calls itself "Dijkstra" but pops from a plain FIFO queue is BFS. A heap keyed by distance on this unit grid is DIJK even though it behaves like BFS.
- To save reading: identical programs (after stripping comments and whitespace) get one label. Programs with the same signature from the same stage may be labelled by reading 3 of them; if those 3 disagree, read all of that group.
- Unsure? Use OTHER with a note. Do not force a catalogue label.

## 6. Stages

Write each stage's prompts to `prompts/` before generating. After each stage, write its `.jsonl`, look at a few raw outputs yourself, and add two lines to `logs/progress.md`. In the prompts below `{SPEC}` is the task text.

### Stage 0. Smoke test (stop gate)

Generate 10 answers to `{SPEC}` alone and run the tests.

- **Stop and report** if fewer than 5 of 10 pass all tests (the model is too weak for this task as posed), or if generation is slower than about 2 minutes per batch of 8.

### Stage A. Unprompted

Prompt: `{SPEC}`. **50 samples.**
Gives the default method and its share.

### Stage B. What it lists

Prompt: `{SPEC}` followed by: *"Do not write code. List every different algorithm or approach that could solve this task, one per line, with a one-sentence description."* **10 samples.**

You map every listed item to a catalogue id or OTHER. Record for each catalogue method in how many of the 10 lists it appears. Add any sensible listed method that is not in the catalogue as an extra row (id `X1`, `X2`, ...) and carry it through stages C and E.

### Stage C. Implement by name

For every catalogue method (and extra rows): *"Implement this task using {method name}."* + `{SPEC}`. **10 samples each.**

Each sample gets one outcome:

| Outcome | Meaning |
|---|---|
| RIGHT | judged to be that method and passes all tests |
| BROKEN | judged to be that method, fails tests |
| SWAPPED | a different method |
| JUNK | no usable program |

A method is **KNOWN** if at least 3 of 10 are RIGHT. For the three methods marked "no" in the catalogue, count BROKEN as RIGHT if the code is a faithful version of the method. Everything else is **UNKNOWN**.

### Stage D. The tree

Maps what the model writes when nobody steers it, including rare branches that 50 samples would never show.

Because only one model fits in memory, the tree is built **level by level**, with everything the other model needs saved to disk in between. One level = three passes:

```
SURE=0.90  MIN_P=0.03  K=5  R=4  MAX_FORKS=3  MAX_POINTS=15  MAX_ROLLOUTS=800

open = [ (prefix=empty, mass_tuned=1, mass_base=1, forks=0) ]

while open is not empty:
    # PASS 1 (tuned loaded): for every open prefix, one greedy completion,
    #   keeping the probability of every step.
    #   points = positions where the top-1 probability < SURE   (earliest first, at most MAX_POINTS)
    #   save every (prefix, point, tuned top-1 token and probability) to disk

    # PASS 2 (base loaded): for every saved point, the base model's next-token probabilities.
    #   cands = base top-K tokens with probability >= MIN_P, plus the tuned top-1
    #   save to disk

    # PASS 3 (tuned loaded): for every point and every candidate token,
    #   R sampled completions of (text up to the point + token); compute their signatures.
    #   Then, per greedy path, walk its points in order:
    #     - every option gives the same majority signature  -> wording only, next point
    #     - otherwise it is a real fork: group options by majority signature;
    #       for each group other than the one holding the tuned top-1,
    #       take its most probable token and multiply the masses
    #       (tuned: p_tuned(token); base: sum of p_base over the group);
    #         all R rollouts agree        -> save a leaf
    #         else, if forks < MAX_FORKS  -> add (text up to point + token) to next level's open list
    #       count one fork for this path and keep walking its points
    #   the greedy completion itself is saved as a leaf
    open = next level's open list
```

That is at most `MAX_FORKS + 1` levels, so about four swaps to the base model in total.

- The prompt is the stage A prompt. Rollouts at points that come after a real fork on the same greedy path are still run (simpler, a little wasteful). Stop when `MAX_ROLLOUTS` is used up and say so.
- Every rollout is saved and goes to the judging sheet.
- Output: one row per leaf with the forking position, the forced token, the judged method, pass rate of its rollouts, and its probability under the tuned and the base model.
- Also report plainly: how many hesitation points there were, how many were wording only, how many were real forks.

### Stage E. Hint ladder

For every method except the stage A default, how much help does it need? **10 samples per level.**

| Level | Prompt added to `{SPEC}` | New runs? |
|---|---|---|
| H0 | nothing | no, reuse stage A |
| H1 | "Use the approach whose name starts with the letter '{first letter}'." | yes |
| H2 | "{name} is one well-known approach to this task; implement any correct algorithm." | yes |
| H3 | "Implement this task using {name}." | no, reuse stage C |
| H4 | the catalogue's one-sentence mechanism, with no method name | yes |
| H5 | 5–8 lines of pseudo-code you write for the method, with no method name | yes |

Result per method: the **lowest level at which at least 5 of 10 are RIGHT** (or "never").

H1–H3 measure whether the model already has the method. H4–H5 measure whether it can follow instructions. A method first reached at H4 or H5 was not known.

### Stage F. Three ways to push it off the default

Run all three for every non-default catalogue method where it applies. The interesting rows are the UNKNOWN methods and those that needed H4 or more.

**F1. Change the problem.** For each method, add a requirement to the task that makes that method the natural answer **without naming it and without describing its mechanism**. Leaking toward one answer is intended; saying the answer is not. Keep the function signature so the 48 tests still apply. **10 samples each.** Starting points (improve them, save the final text first):

| Target | Added requirement |
|---|---|
| DFS | "No imports and no queue-like containers are allowed; extra memory must stay proportional to the length of the path." |
| IDDFS | "Extra memory must stay proportional to the length of the path, and the returned path must be a shortest one." |
| BIDIR | "Grids are huge and open, start and goal are far apart, and exploring outward from only one of them is too slow." |
| ASTAR | "Grids are huge and mostly open; examine as few cells as possible, and the returned path must be a shortest one. You know where the goal is." |
| GREEDY | "Grids are huge and mostly open; examine as few cells as possible. Path length does not matter. You know where the goal is." |
| DIJK | "The same code will later be reused on grids where entering a cell has a cost from 1 to 9, so write it so that only the cost lookup has to change." |
| WAVE | "A robot will follow your result. It can only read a number stored in its own cell and its four neighbours, so prepare the numbers first and then let it walk." |
| RELAX | "No queue, stack, heap, set, dictionary or recursion is allowed: only for-loops over the whole grid and one 2D list of numbers." |
| DEADEND | "You may not keep any record of visited cells or any list of cells to process. The only thing you may change is the grid itself, by turning free cells into walls." |
| WALL | "The solver may remember only its current cell and the direction it faces. Nothing else." |
| RANDOM | "The solver may remember only its current cell. A random number generator is available." |

Judge two things per sample: which method it is, and whether it actually respects the added requirement.

**F2. Scoring loop.** One loop, one score, not aimed at any single method.

- Score = average number of grid-cell reads over the 48 tests (lower is better), counted by passing the grid as small wrapper objects that count indexing. Programs that fail any test get no score. First compute the score of the six reference files for context.
- Start from the 3 best stage A programs. Each round: show the current top 3 with their scores and ask *"Write a different solve that passes the same tests and reads fewer cells."* 8 new programs per round, **8 rounds**. Keep the best 3 distinct programs.
- Report the score curve and the judged method of every program that entered the top 3.

**F3. Reject repeats.** A conversation, **5 chains of up to 8 steps**.

- Step 1: `{SPEC}`. After each answer compute its signature.
- Same signature as an earlier answer in the chain: reply *"Rejected: this works the same way as your attempt #{k}. Write a solution that works in a fundamentally different way."*
- Fails tests: reply *"Rejected: it fails the tests ({n} of 48 pass). Fix it or try another approach."*
- New signature and passes: reply *"Accepted. Now write another solution that works in a fundamentally different way from all your previous ones."*
- Never name a method in the feedback. Report, per chain, the sequence of judged methods.

### Stage G. Judge

Do the judging (5.4) after all generation is finished, in one pass over the shuffled sheet. Then join labels back to stages.

## 7. Size and time

About 1,700 generations of at most 700 tokens, a few GPU hours. Run stages in order, one background job per stage, and check each result before starting the next. If something takes far longer than expected, cut sample counts in half before cutting stages, and record it.

## 8. What to deliver: `round-map/README.md`

Short, plain, tables first. A reader should understand it without this plan.

1. Three lines: model, task, what was run and what was cut.
2. **The map.** One row per catalogue method (plus extras):

| Method | Listed (of 10) | Unprompted (of 50) | In the tree? (prob. tuned / base) | By name (RIGHT / BROKEN / SWAPPED / JUNK) | KNOWN? | Lowest hint level | F1 problem change (of 10) | F2 loop | F3 rejection |
|---|---|---|---|---|---|---|---|---|---|

3. **The tree**, drawn as indented text: position, token, where each branch leads.
4. **Did it get outside its map?** List every UNKNOWN method (or one first reached at H4+) that came out RIGHT in F1, F2 or F3, with the program. If there are none, say "none".
5. **OTHER pile:** every distinct OTHER program that passes all tests, with your one-line description.
6. **Problems:** what failed, what you are unsure about in your own judging (give counts), anything that looks wrong.
7. How to re-run each stage (one command each).

End your final message with the same summary in a few lines. Do not commit.
