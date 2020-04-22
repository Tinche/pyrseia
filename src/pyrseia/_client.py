from inspect import getfullargspec
from typing import AsyncContextManager, Awaitable, Callable, Type, TypeVar
from weakref import WeakKeyDictionary

from cattr import Converter
from msgpack import dumps, loads
from wrapt import decorator  # type: ignore

from .wire import Call

converter = Converter()

T = TypeVar("T")
ClientAdapter = Callable[[bytes], Awaitable[bytes]]

_clients: WeakKeyDictionary = WeakKeyDictionary()


async def create_client(
    api: Type[T], network_adapter: AsyncContextManager[ClientAdapter]
) -> T:
    class Client(api):  # type: ignore
        pass

    sender = await network_adapter.__aenter__()

    for name in dir(Client):
        obj = getattr(Client, name)
        if hasattr(obj, "__is_rpc"):
            setattr(Client, name, _adjust_rpc(obj, sender))

    res = Client()
    _clients[res] = network_adapter
    return res


async def close_client(client):
    await _clients[client].__aexit__(None, None, None)


def _adjust_rpc(coro, sender: ClientAdapter):
    argspec = getfullargspec(coro)
    return_type = argspec.annotations["return"]

    @decorator
    async def wrapper(wrapped, instance, args, kwargs):
        payload = dumps(converter.unstructure(Call(coro.__name__, args)))
        resp_payload = await sender(payload)
        return converter.structure(loads(resp_payload), return_type)

    return wrapper(coro)
