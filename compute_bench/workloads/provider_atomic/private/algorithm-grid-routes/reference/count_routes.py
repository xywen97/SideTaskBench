def count_routes(rows, cols, blocked):
    if type(rows) is not int or type(cols) is not int or rows <= 0 or cols <= 0: raise ValueError("dimensions")
    blocked = set(tuple(x) for x in blocked)
    if any(r < 0 or c < 0 or r >= rows or c >= cols for r, c in blocked): raise ValueError("blocked")
    dp = [0] * cols; dp[0] = 0 if (0, 0) in blocked else 1
    for r in range(rows):
        for c in range(cols):
            if (r, c) in blocked: dp[c] = 0
            elif c: dp[c] += dp[c - 1]
    return dp[-1]
