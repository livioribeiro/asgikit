from collections.abc import Callable
from functools import partial
from typing import Concatenate, ParamSpec, TypeVar

__all__ = ("CallableProxy",)

T = TypeVar("T")
P = ParamSpec("P")


class CallableProxy:
    __slots__ = ("func",)

    def __init__(self, func: Callable[P, T]):
        self.func = func

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.func(*args, **kwargs)

    def wrap(self, wrapper: Callable[Concatenate[Callable[P, T], P], T]):
        self.func = partial(wrapper, self.func)
