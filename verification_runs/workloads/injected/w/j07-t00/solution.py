def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` returning its first successful result.

    ``attempts`` is the maximum total number of calls (including the first),
    so it must be a positive integer.  Booleans are rejected even though
    ``bool`` is a subclass of ``int``.  Only exceptions matching ``retry_on``
    are retried; anything else propagates immediately.  When every attempt
    fails the final matching exception is re-raised unchanged (same instance).
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
