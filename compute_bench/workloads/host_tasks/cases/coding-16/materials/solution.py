def normalize_mailboxes(values):
    return [{'name':'','address':value.strip()} for value in values]
