"""The catalogue (PLAN section 4) plus per-method prompt material for stages C, E, F1.
Extras found in stage B are added from results/extras.json (same fields)."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# id: (name used in prompts, first letter for H1, one-sentence mechanism (H4), pure version passes all tests?)
CAT = {
    "BFS": ("breadth-first search", "B",
            "Explore cells in rings of increasing distance from the start using a first-in-first-out queue, remembering each cell's predecessor.", True),
    "DFS": ("depth-first search", "D",
            "Keep going forward into an unvisited neighbour as far as possible and step back only when stuck (recursion or an explicit stack).", True),
    "IDDFS": ("iterative deepening depth-first search", "I",
              "Run a depth-limited forward search again and again, raising the depth limit by one each time.", True),
    "BIDIR": ("bidirectional search", "B",
              "Grow one search from the start and one from the goal in turns and stop when they touch, then join the two half-paths.", True),
    "ASTAR": ("A* search", "A",
              "Always expand the cell with the smallest (steps so far + straight-line estimate to the goal), using a priority queue.", True),
    "GREEDY": ("greedy best-first search", "G",
               "Always expand the cell that looks closest to the goal, ignoring steps so far, using a priority queue.", True),
    "DIJK": ("Dijkstra's algorithm", "D",
             "Always expand the cell with the smallest steps-so-far using a priority queue of distances.", True),
    "WAVE": ("the wavefront (Lee) algorithm", "W",
             "First write into every reachable cell its distance from the goal, then walk from the start always stepping to a neighbour with a smaller number.", True),
    "RELAX": ("sweep relaxation (Bellman-Ford style)", "S",
              "With no queue at all, sweep over the whole grid repeatedly, lowering each cell's distance from its neighbours, until a sweep changes nothing.", True),
    "DEADEND": ("dead-end filling", "D",
                "Repeatedly turn free cells that have only one free neighbour (and are not start or goal) into walls, until none are left.", False),
    "WALL": ("the wall follower algorithm", "W",
             "Keep one hand on the wall: store only position and facing direction, and always try to turn the same way first.", False),
    "RANDOM": ("a random walk", "R",
               "Step to a random free neighbour until the goal is reached.", False),
}

# H5: 5-8 lines of pseudo-code, no method name.
PSEUDO = {
    "DFS": """1. if start or goal is a wall, return []
2. path = [start]; visited = {start}
3. while path is not empty:
4.     cell = last element of path; if cell is goal, return path
5.     pick any free neighbour of cell that is not in visited
6.     if there is one: add it to visited and append it to path
7.     otherwise: remove the last element of path
8. return []""",
    "IDDFS": """1. if start or goal is a wall, return []
2. for limit = 0, 1, 2, ... up to rows*cols:
3.     path = [start]
4.     call probe(start, limit); if it returns true, return path
5. return []
6. probe(cell, budget): if cell is goal return true; if budget is 0 return false
7.     for each free neighbour n of cell that is not already in path:
8.         append n to path; if probe(n, budget - 1) return true; otherwise remove n from path. Finally return false""",
    "BIDIR": """1. if start or goal is a wall, return []; if start equals goal, return [start]
2. cameA = {start: None}; frontA = [start]; cameB = {goal: None}; frontB = [goal]
3. while frontA and frontB are both non-empty:
4.     take the side with the smaller front; build its next front from the free neighbours of its front cells that are not yet in its own came-map, recording for each the cell it was reached from
5.     if a newly added cell m is also in the other side's came-map: stop the loop with meeting cell m
6.     replace that side's front by the new front
7. if no meeting cell was found, return []
8. follow cameA from m back to start and reverse it, then follow cameB from m to goal; return the two pieces joined""",
    "ASTAR": """1. if start or goal is a wall, return []
2. h(cell) = |cell.row - goal.row| + |cell.col - goal.col|
3. g = {start: 0}; came = {start: None}; heap = [(h(start), 0, start)]
4. while heap is not empty:
5.     pop the entry with the smallest first element; let cell be its cell; if cell is goal, rebuild the path through came and return it
6.     for each free neighbour n of cell: new = g[cell] + 1
7.         if n is not in g or new < g[n]: g[n] = new; came[n] = cell; push (new + h(n), new, n)
8. return []""",
    "GREEDY": """1. if start or goal is a wall, return []
2. h(cell) = |cell.row - goal.row| + |cell.col - goal.col|
3. came = {start: None}; heap = [(h(start), start)]
4. while heap is not empty:
5.     pop the entry with the smallest h; let cell be its cell; if cell is goal, rebuild the path through came and return it
6.     for each free neighbour n of cell that is not in came:
7.         came[n] = cell; push (h(n), n)
8. return []""",
    "DIJK": """1. if start or goal is a wall, return []
2. dist = {start: 0}; came = {start: None}; heap = [(0, start)]
3. while heap is not empty:
4.     pop the entry (d, cell) with the smallest d; if d > dist[cell], skip it
5.     if cell is goal, rebuild the path through came and return it
6.     for each free neighbour n of cell: new = d + 1
7.         if n is not in dist or new < dist[n]: dist[n] = new; came[n] = cell; push (new, n)
8. return []""",
    "WAVE": """1. if start or goal is a wall, return []
2. num = a rows x cols table filled with -1; num[goal] = 0; layer = [goal]; k = 0
3. while layer is not empty:
4.     k = k + 1; next = every free cell with num == -1 that is adjacent to a cell of layer; set num of each to k; layer = next
5. if num[start] == -1, return []
6. path = [start]; cell = start
7. while cell is not goal: move cell to an adjacent cell whose num is exactly num[cell] - 1; append it to path
8. return path""",
    "RELAX": """1. if start or goal is a wall, return []
2. INF = rows*cols + 1; d = a rows x cols table filled with INF; d[goal] = 0
3. repeat:
4.     changed = false
5.     for every row r and every column c with a free cell: m = 1 + the smallest d among its free 4-neighbours; if m < d[r][c]: d[r][c] = m; changed = true
6. until changed is false
7. if d[start] == INF, return []
8. path = [start]; from the current cell keep stepping to a neighbour whose d is one less, appending it, until goal; return path""",
    "DEADEND": """1. if start or goal is a wall, return []; if start equals goal, return [start]
2. g = a mutable copy of the grid
3. repeat until a full pass changes nothing:
4.     for every free cell of g other than start and goal: if it has at most one free 4-neighbour in g, turn it into a wall
5. if start now has no free neighbour, return []
6. path = [start]; prev = None; cell = start
7. while cell is not goal: step to a free neighbour of cell in g that is not prev (return [] if there is none); prev = old cell; append the new cell to path
8. return path""",
    "WALL": """1. if start or goal is a wall, return []; path = [start]; cell = start; facing = up
2. repeat at most 4*rows*cols + 4 times:
3.     if cell is goal, return path
4.     for turn in (right of facing, facing, left of facing, opposite of facing), in this order:
5.         if the cell one step in direction turn is inside the grid and free:
6.             facing = turn; cell = that cell; append cell to path; stop trying turns
7. return []""",
    "RANDOM": """1. if start or goal is a wall, return []
2. cell = start; path = [start]
3. repeat at most 200000 times:
4.     if cell is goal, return path
5.     options = the free 4-neighbours of cell; if there are none, return []
6.     cell = one of options chosen uniformly at random; append cell to path
7. return []""",
}

# F1: added requirement that makes the method natural without naming or describing it.
F1 = {
    "DFS": "No imports and no queue-like containers are allowed; extra memory must stay proportional to the length of the path.",
    "IDDFS": "Extra memory must stay proportional to the length of the path, and the returned path must be a shortest one.",
    "BIDIR": "Grids are huge and open, start and goal are far apart, and exploring outward from only one of them is too slow.",
    "ASTAR": "Grids are huge and mostly open; examine as few cells as possible, and the returned path must be a shortest one. You know where the goal is.",
    "GREEDY": "Grids are huge and mostly open; examine as few cells as possible. Path length does not matter. You know where the goal is.",
    "DIJK": "The same code will later be reused on grids where entering a cell has a cost from 1 to 9, so write it so that only the cost lookup has to change.",
    "WAVE": "A robot will follow your result. It can only read a number stored in its own cell and its four neighbours, so prepare the numbers first and then let it walk.",
    "RELAX": "No queue, stack, heap, set, dictionary or recursion is allowed: only for-loops over the whole grid and one 2D list of numbers.",
    "DEADEND": "You may not keep any record of visited cells or any list of cells to process. The only thing you may change is the grid itself, by turning free cells into walls.",
    "WALL": "The solver may remember only its current cell and the direction it faces. Nothing else.",
    "RANDOM": "The solver may remember only its current cell. A random number generator is available.",
}


def load():
    """Returns dict id -> dict(name, letter, mech, pure_ok, pseudo, f1). Includes stage-B extras if present."""
    out = {}
    for k, (name, letter, mech, ok) in CAT.items():
        out[k] = dict(name=name, letter=letter, mech=mech, pure_ok=ok, pseudo=PSEUDO.get(k), f1=F1.get(k))
    p = os.path.join(ROOT, "results", "extras.json")
    if os.path.exists(p):
        for k, v in json.load(open(p)).items():
            out[k] = v
    return out
