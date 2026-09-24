def retry_call(operation, attempts=3, retry_on=(Exception,)):
    for index in range(attempts + 1):
        try:
            return operation()
        except retry_on:
            if index == attempts:
                raise
