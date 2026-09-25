def adapt_retry(config):
    return {"max_attempts": config["attempts"], "base_delay_seconds": config["delay_ms"] / 1000, "retry_codes": list(config["codes"])}
