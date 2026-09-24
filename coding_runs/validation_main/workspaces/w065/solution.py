def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` up to ``attempts`` total times.

    ``attempts`` is the maximum total number of calls (including the
    first), not the number of retries after an initial call. It must be a
    positive integer excluding ``bool``; otherwise :class:`ValueError` is
    raised before ``operation`` is ever called.

    Only exceptions matching ``retry_on`` are retried. Non-matching
    exceptions propagate immediately. If every attempt raises a matching
    exception, the final exception instance is re-raised unchanged.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer excluding bool")

    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
