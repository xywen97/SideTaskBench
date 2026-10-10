def csv_quoted_record_splitter(csv_text):
    records, current, quoted = [], [], False
    for char in csv_text:
        if char == '"':
            quoted = not quoted
        if char == "\n" and not quoted:
            records.append("".join(current))
            current = []
        else:
            current.append(char)
    if current:
        records.append("".join(current))
    return records
