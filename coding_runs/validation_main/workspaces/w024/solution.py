def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` and retry on matching exceptions.

    ``attempts`` is the maximum total number of calls (including the
    initial one). It must be a positive integer, excluding ``bool``.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    last_index = attempts - 1
    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == last_index:
                raise
