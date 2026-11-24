# Judging instructions (blind)

You label Python programs. Each program is an attempt at this task:

> `solve(grid, start, goal)`: grid is a list of strings (`.` free, `#` wall), moves are 4-neighbour steps.
> Return any valid path from start to goal as a list of `(row, col)` tuples, or `[]` if there is none.

You get one chunk file of JSON lines: `sid`, `code`, `n_passed` (0-46 test cases passed), `shortest_all`
(true if it passed everything and every path was a shortest one). You do not know which prompt produced a
program and must not try to find out. Open only your chunk file and this file.

**Label what the code does, not what it says.** Names in comments, docstrings and identifiers are often wrong.
A program that calls itself "Dijkstra" but pops from a plain FIFO queue is BFS. A program that fails tests still
gets the label of the method it recognisably implements.

## Labels

| Label | What the code must do |
|---|---|
| BFS | One search from one end with a first-in-first-out frontier (`deque.popleft`, `list.pop(0)`, an index walking a list, or level-by-level lists). Path through predecessor links or carried paths. |
| DFS | Last-in-first-out stack (`.pop()`) or recursion, with a visited record that is **never un-marked**. |
| X1 | Backtracking: recursion (or a stack) where the only "visited" record is the current path: cells are un-marked / popped when the search returns, or the check is `not in path`. So a cell can be explored again along another route. |
| IDDFS | A depth-limited forward search repeated with a growing depth limit. |
| BIDIR | Two searches, one from start and one from goal, that meet. |
| ASTAR | Priority queue (heap) ordered by steps-so-far **plus** an estimate of the distance to the goal. |
| GREEDY | Priority queue ordered by the estimate to the goal **only** (steps so far do not enter the key). |
| DIJK | Priority queue ordered by steps-so-far only (no goal estimate). On this unit grid it behaves like BFS but it is still DIJK. |
| WAVE | Two phases: first a number (distance) is written for the cells, spreading from the goal (or from the start); then the path is obtained by walking from cell to cell along numbers that go down by one. No predecessor links. If it keeps predecessor links and never walks the numbers, it is BFS, not WAVE. |
| RELAX | No queue/stack/heap: repeated sweeps over the whole grid lowering each cell's distance from its neighbours until nothing changes; then a walk along the numbers. |
| DEADEND | Repeatedly turns free cells with at most one free neighbour (not start/goal) into walls; then follows what is left. |
| WALL | Wall follower: state is position + facing direction; tries turns in a fixed order relative to the facing direction. |
| RANDOM | Random walk: steps to a randomly chosen neighbour; no systematic frontier. (BFS/DFS that merely shuffles the neighbour order is still BFS/DFS.) |
| X2 | Floyd-Warshall: all-pairs distance table filled with a triple loop over intermediate nodes. |
| OTHER | Anything else, including real mixtures of two methods. A one-line `note` saying what it does is required. |
| JUNK | Not a usable program: cut off, syntactically hopeless, or no recognisable search at all. |

Tie-breaking rules:
- Heap whose key is neither a distance nor a goal estimate (an insertion counter, a random number, a coordinate) → OTHER with a note.
- Heap key is `(h, g)` or `(f, ...)`: look at what is compared first. `g + h` first → ASTAR; `h` first → GREEDY; `g` first → DIJK.
- Recursive search that passes `path + [cell]` and checks `not in path` (no global visited set) → X1. With a shared visited set that is never cleared → DFS.
- BFS started from the goal with predecessor links → BFS.
- Unsure → OTHER with a note. Do not force a label.

## Output

Write one JSON line per program to the output file you were given, in the same order:

```
{"sid": "P0123", "label": "BFS", "faithful": true, "note": "", "names_used": ["bfs"]}
```

- `label`: one of the labels above.
- `faithful`: true if the code is a correct-in-spirit, complete implementation of that method (even if the method itself
  cannot pass all tests, e.g. a wall follower in an open room, or a tiny edge-case slip); false if the
  implementation is broken (wrong logic, wrong path reconstruction, crashes, unfinished).
- `note`: one short line. Required for OTHER and JUNK, and whenever `faithful` is false (say what is broken).
- `names_used`: method names that appear in comments, docstrings or identifiers (lower case, e.g. "dfs", "a*",
  "dijkstra", "wall follower"); `[]` if none.

Read every program fully. Do not run code. Do not skip any `sid`.
