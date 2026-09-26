def rolling_summary(values, width, min_valid=1):
    return [{'mean': sum(values[i:i+width])/width} for i in range(len(values)-width+1)]
