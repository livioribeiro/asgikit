from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple

__all__ = ("AsgiContext",)


class AsgiContext(NamedTuple):
    scope: dict[str, Any]
    receive: Callable[[], Awaitable[dict[str, Any]]]
    send: Callable[[dict[str, Any]], Awaitable]
