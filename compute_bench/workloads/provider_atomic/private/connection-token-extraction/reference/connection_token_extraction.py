def connection_token_extraction(connection_value):
    return [token.strip() for token in connection_value.split(",") if token.strip()]
