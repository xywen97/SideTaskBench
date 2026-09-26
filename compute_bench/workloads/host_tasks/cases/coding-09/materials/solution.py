def build_copy_plan(root, entries):
    return [{**entry, 'target': root + '/' + entry['path']} for entry in entries]
