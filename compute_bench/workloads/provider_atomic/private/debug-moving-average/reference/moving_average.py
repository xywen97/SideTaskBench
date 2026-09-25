def moving_average(values, width):
    if type(width) is not int or width <= 0 or width > len(values):
        raise ValueError("invalid width")
    return [sum(values[i:i + width]) / width for i in range(len(values) - width + 1)]
