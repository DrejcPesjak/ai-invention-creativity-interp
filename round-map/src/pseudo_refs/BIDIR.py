def solve(grid, start, goal):
    if _wall(grid, start, goal): return []
    if start == goal: return [start]
    cameA = {start: None}; frontA = [start]; cameB = {goal: None}; frontB = [goal]
    m = None
    while frontA and frontB and m is None:
        if len(frontA) <= len(frontB):
            came, other, front, side = cameA, cameB, frontA, 'A'
        else:
            came, other, front, side = cameB, cameA, frontB, 'B'
        new = []
        for c in front:
            for n in _nb(grid, c):
                if n not in came:
                    came[n] = c; new.append(n)
                    if n in other and m is None: m = n
        if side == 'A': frontA = new
        else: frontB = new
    if m is None: return []
    a = []; c = m
    while c is not None: a.append(c); c = cameA[c]
    a.reverse()
    c = cameB[m]
    while c is not None: a.append(c); c = cameB[c]
    return a
