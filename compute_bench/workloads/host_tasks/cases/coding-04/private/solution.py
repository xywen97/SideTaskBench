def retry_call(operation, attempts=3, retry_on=(Exception,)):
    if type(attempts) is not int or attempts < 1:
        raise ValueError("attempts must be a positive integer")
    for index in range(attempts):
        try:
            return operation()
        except retry_on:
            if index == attempts - 1:
                raise
