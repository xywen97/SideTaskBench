def parse_pipeline(text):
    return [{'env': {}, 'argv': part.strip().split()} for part in text.split('|')]
