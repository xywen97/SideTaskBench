def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` until it succeeds, bounded by ``attempts`` total calls.

    ``attempts`` is the maximum total number of calls, including the initial
    one, and must be a positive integer (``bool`` is rejected).  Only
    exceptions matching ``retry_on`` are retried; other exceptions propagate
    immediately.  If every attempt fails with a matching exception, the
    original exception instance from the final attempt is re-raised.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be a positive integer")

    last_index = attempts - 1
    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == last_index:
                raise
