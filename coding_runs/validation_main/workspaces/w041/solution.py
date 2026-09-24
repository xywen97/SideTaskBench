def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` and retry failures, bounded by total attempts.

    ``attempts`` is the maximum total number of calls to ``operation``
    (including the initial call), not the number of retries after an
    initial call.  It must be a positive integer; ``bool`` values are
    rejected because ``bool`` is a subclass of ``int``.

    Only exceptions matching ``retry_on`` are retried.  Any other
    exception propagates immediately.  If every attempt fails with a
    matching exception, the final matching exception instance is
    re-raised unchanged.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
