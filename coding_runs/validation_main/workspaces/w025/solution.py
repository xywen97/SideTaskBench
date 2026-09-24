def retry_call(operation, attempts=3, retry_on=(Exception,)):
    """Call ``operation`` up to ``attempts`` total times, retrying on ``retry_on``.

    ``attempts`` is the maximum total number of calls (including the first),
    not the number of retries after an initial call. It must be a positive
    integer excluding ``bool``; otherwise ``ValueError`` is raised before
    ``operation`` is ever called.

    Only exceptions matching ``retry_on`` are retried. Any other exception
    propagates immediately. If every attempt raises a matching exception, the
    final exception instance is re-raised unchanged.
    """
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts <= 0:
        raise ValueError("attempts must be a positive integer")

    last_exc = None
    for _ in range(attempts):
        try:
            return operation()
        except retry_on as exc:
            last_exc = exc
    # Every attempt raised a matching exception; re-raise the final instance.
    raise last_exc
