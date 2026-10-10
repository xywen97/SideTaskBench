def utc_offset_parser(offset_str):
    sign = -1 if offset_str.startswith("-") else 1
    hours, minutes = offset_str.lstrip("+-").split(":")
    hours, minutes = sign * int(hours), sign * int(minutes)
    return {"hours": hours, "minutes": minutes, "total_minutes": hours * 60 + minutes}
