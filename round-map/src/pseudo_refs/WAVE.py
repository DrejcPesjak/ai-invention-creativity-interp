def solve(grid, start, goal):
    if _wall(grid, start, goal): return []
    R, C = len(grid), len(grid[0])
    num = [[-1] * C for _ in range(R)]; num[goal[0]][goal[1]] = 0; layer = [goal]; k = 0
    while layer:
        k += 1; nxt = []
        for c in layer:
            for n in _nb(grid, c):
                if num[n[0]][n[1]] == -1:
                    num[n[0]][n[1]] = k; nxt.append(n)
        layer = nxt
    if num[start[0]][start[1]] == -1: return []
    path = [start]; cell = start
    while cell != goal:
        cell = next(n for n in _nb(grid, cell) if num[n[0]][n[1]] == num[cell[0]][cell[1]] - 1)
        path.append(cell)
    return path
