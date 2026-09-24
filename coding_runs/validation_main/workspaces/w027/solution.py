def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` up to ``attempts`` total times.

    ``attempts`` bounds the total number of calls (including the first
    one), not the number of retries after an initial call.  Only
    exceptions matching ``retry_on`` are retried; any other exception
    propagates immediately.  If every attempt raises a matching
    exception, the final exception instance is re-raised unchanged.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
