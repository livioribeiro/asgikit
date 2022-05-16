def fibonacci(limit: int):
    first = 0
    second = 1

    for i in range(0, limit):
        yield first
        first, second = second, first + second
