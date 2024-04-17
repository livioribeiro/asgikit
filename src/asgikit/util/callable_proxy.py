from collections.abc import Callable
from functools import partial
from typing import Any, Concatenate, ParamSpec

__all__ = ("CallableProxy",)

P = ParamSpec("P")


class CallableProxy:
    __slots__ = ("func",)

    def __init__(self, func: Callable[P, Any]):
        self.func = func

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        return self.func(*args, **kwargs)

    def wrap(self, wrapper: Callable[Concatenate[Callable[P, Any], P], Any]):
        self.func = partial(wrapper, self.func)
