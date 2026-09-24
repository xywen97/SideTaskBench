def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` at most ``attempts`` times.

    ``attempts`` is the maximum total number of calls, including the first
    one. It must be a positive integer (``bool`` is rejected), otherwise a
    ``ValueError`` is raised before ``operation`` is invoked.

    Only exceptions matching ``retry_on`` are retried. Any other exception
    propagates immediately, and if every attempt raises a matching exception
    the final one is re-raised unchanged (same instance and traceback).
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
