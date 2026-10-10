def placeholder_boundary_scan(template):
    found, index = [], 0
    while index < len(template):
        if template.startswith("$$", index):
            index += 2
            continue
        if template.startswith("${", index):
            close = template.find("}", index + 2)
            if close == -1:
                break
            found.append({"start": index, "end": close + 1, "name": template[index + 2:close]})
            index = close + 1
            continue
        index += 1
    return found
