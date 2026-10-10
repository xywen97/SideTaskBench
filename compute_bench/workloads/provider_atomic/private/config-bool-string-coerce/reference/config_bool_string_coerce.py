def config_bool_string_coerce(config):
    mapping = {"true": True, "false": False}
    return {key: mapping[value] if isinstance(value, str) and value in mapping else value
            for key, value in config.items()}
