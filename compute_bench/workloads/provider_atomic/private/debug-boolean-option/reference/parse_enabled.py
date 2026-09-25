def parse_enabled(value):
    if type(value) is bool:
        return value
    if isinstance(value, str):
        key = value.strip().casefold()
        if key in {"true", "1", "yes"}: return True
        if key in {"false", "0", "no"}: return False
    raise ValueError("invalid boolean")
