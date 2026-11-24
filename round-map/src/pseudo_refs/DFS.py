def solve(grid, start, goal):
    if _wall(grid, start, goal): return []
    path = [start]; visited = {start}
    while path:
        cell = path[-1]
        if cell == goal: return path
        n = next((x for x in _nb(grid, cell) if x not in visited), None)
        if n is not None:
            visited.add(n); path.append(n)
        else:
            path.pop()
    return []
