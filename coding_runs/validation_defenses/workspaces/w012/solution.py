def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` up to ``attempts`` total times.

    ``attempts`` is the maximum number of calls (including the first), not
    the number of retries after an initial call. It must be a positive
    integer other than ``bool``; otherwise ``ValueError`` is raised before
    ``operation`` is ever called.

    Only exceptions matching ``retry_on`` are retried. Non-matching
    exceptions propagate immediately, and if every attempt fails the final
    matching exception is re-raised as the original instance.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")
    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
