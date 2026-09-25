def batch_ranges(length, size):
    if type(length) is not int or length < 0 or type(size) is not int or size <= 0:
        raise ValueError("invalid range")
    return [(i, min(i + size, length)) for i in range(0, length, size)]
