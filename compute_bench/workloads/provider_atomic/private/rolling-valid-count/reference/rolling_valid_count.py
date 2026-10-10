def rolling_valid_count(values, window_size):
    counts = []
    for index in range(len(values)):
        window = values[max(0, index - window_size + 1):index + 1]
        counts.append(sum(value is not None for value in window))
    return counts
