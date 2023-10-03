from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple, TypeAlias

__all__ = (
    "AsgiScope",
    "AsgiReceive",
    "AsgiSend",
    "AsgiProtocol",
)


AsgiScope: TypeAlias = dict[str, Any]
AsgiReceive: TypeAlias = Callable[..., Awaitable[dict]]
AsgiSend: TypeAlias = Callable[[dict], Awaitable]


class AsgiProtocol(NamedTuple):
    scope: AsgiScope
    receive: AsgiReceive
    send: AsgiSend
