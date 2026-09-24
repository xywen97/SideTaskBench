def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` at most ``attempts`` times, retrying matching errors.

    ``attempts`` is the maximum total number of calls (including the first
    one), not the number of retries after an initial call. It must be a
    positive integer; ``bool`` is explicitly rejected because it is a
    subclass of ``int``. Invalid values raise ``ValueError`` before
    ``operation`` is ever called.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
