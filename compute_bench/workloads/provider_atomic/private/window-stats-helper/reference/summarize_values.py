def summarize_values(values):
    numbers = [value for value in values if value is not None]
    if not numbers:
        return {"count": 0, "min": None, "max": None, "range": None}
    low = min(numbers)
    high = max(numbers)
    return {"count": len(numbers), "min": low, "max": high, "range": high - low}
