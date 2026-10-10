from decimal import Decimal


def decimal_quantize_rounding(value, precision, mode):
    return str(Decimal(value).quantize(Decimal(precision), rounding=mode))
