def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` returning its first successful result.

    ``attempts`` is the maximum *total* number of calls (including the
    initial one), not the number of retries after an initial call.  It
    must be a positive integer (``bool`` is rejected).  Only exceptions
    matching ``retry_on`` are retried; any other exception propagates
    immediately.  If every attempt raises a matching exception, the final
    exception instance is re-raised unchanged.
    """
    # bool is a subclass of int, so it must be excluded explicitly.
    if isinstance(attempts, bool) or not isinstance(attempts, int):
        raise ValueError("attempts must be a positive integer")
    if attempts < 1:
        raise ValueError("attempts must be a positive integer")

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retry_on:
            if attempt == attempts:
                raise
