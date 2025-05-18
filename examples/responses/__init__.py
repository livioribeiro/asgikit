def fibonacci(limit: int):
    first = 0
    second = 1

    i = 0
    while i < limit:
        i += 1
        yield first
        first, second = second, first + second
