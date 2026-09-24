def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` until it succeeds or ``attempts`` calls are made.

    ``attempts`` is the maximum number of total calls, including the first
    one.  Only exceptions matching ``retry_on`` are retried; any other
    exception propagates immediately.  If every attempt raises a matching
    exception, the final exception instance is re-raised.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
