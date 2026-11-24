def solve(grid, start, goal):
    if _wall(grid, start, goal): return []
    R, C = len(grid), len(grid[0]); INF = R * C + 1
    d = [[INF] * C for _ in range(R)]; d[goal[0]][goal[1]] = 0
    changed = True
    while changed:
        changed = False
        for r in range(R):
            for c in range(C):
                if grid[r][c] == '.':
                    m = 1 + min([d[a][b] for a, b in _nb(grid, (r, c))] or [INF])
                    if m < d[r][c]: d[r][c] = m; changed = True
    if d[start[0]][start[1]] >= INF: return []
    path = [start]; cell = start
    while cell != goal:
        cell = next(n for n in _nb(grid, cell) if d[n[0]][n[1]] == d[cell[0]][cell[1]] - 1)
        path.append(cell)
    return path
