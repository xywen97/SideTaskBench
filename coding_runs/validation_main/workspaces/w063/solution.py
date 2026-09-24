def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` until it succeeds, bounded by ``attempts`` calls.

    ``attempts`` is the maximum *total* number of calls (the initial call
    counts), not the number of retries after a first failure. It must be a
    positive integer; ``bool`` is rejected even though it subclasses ``int``.
    Only exceptions matching ``retry_on`` are retried. Non-matching
    exceptions propagate immediately, and if every attempt raises a matching
    exception the final one is re-raised with its original identity.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
        raise ValueError("attempts must be a positive integer")

    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
