def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` and retry on matching exceptions.

    ``attempts`` is the maximum total number of calls (including the
    initial one). It must be a positive integer (``bool`` is rejected).
    Only exceptions matching ``retry_on`` trigger a retry; any other
    exception propagates immediately. If every attempt fails with a
    matching exception, the final (original) exception instance is
    re-raised.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    last_error = None
    for _ in range(attempts):
        try:
            return operation()
        except retry_on as error:
            last_error = error
    raise last_error
