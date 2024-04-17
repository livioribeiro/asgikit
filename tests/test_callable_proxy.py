from asgikit.util.callable_proxy import CallableProxy


def test_call():
    def func() -> int:
        return 1

    proxy = CallableProxy(func)
    assert proxy() == 1


async def test_call_async():
    async def func() -> int:
        return 1

    proxy = CallableProxy(func)
    assert await proxy() == 1


def test_call_params():
    def func(a: int, b: int) -> int:
        return a + b

    proxy = CallableProxy(func)
    assert proxy(1, 2) == 3


def test_wrap():
    def func() -> int:
        return 1

    def wrapper(f) -> int:
        return f() + 1

    proxy = CallableProxy(func)
    proxy.wrap(wrapper)
    assert proxy() == 2


async def test_wrap_async():
    async def func() -> int:
        return 1

    async def wrapper(f) -> int:
        return await f() + 1

    proxy = CallableProxy(func)
    proxy.wrap(wrapper)
    assert await proxy() == 2


async def test_wrap_async_non_async_wrapper():
    async def func() -> int:
        return 1

    def wrapper(f) -> int:
        return f()

    proxy = CallableProxy(func)
    proxy.wrap(wrapper)
    assert await proxy() == 1


def test_wrap_params():
    def func(a: int, b: int) -> int:
        return a + b

    def wrapper(f, *args, **kwargs) -> int:
        return f(*args, **kwargs) + 1

    proxy = CallableProxy(func)
    proxy.wrap(wrapper)
    assert proxy(2, 3) == 6
