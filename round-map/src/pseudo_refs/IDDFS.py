def solve(grid, start, goal):
    if _wall(grid, start, goal): return []
    path = []
    def probe(cell, budget):
        if cell == goal: return True
        if budget == 0: return False
        for n in _nb(grid, cell):
            if n not in path:
                path.append(n)
                if probe(n, budget - 1): return True
                path.pop()
        return False
    for limit in range(len(grid) * len(grid[0]) + 1):
        path = [start]
        if probe(start, limit): return path
    return []
