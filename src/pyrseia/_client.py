from inspect import getfullargspec
from typing import (
    Any,
    AsyncContextManager,
    Callable,
    Coroutine,
    Generic,
    Type,
    TypeVar,
    overload,
)
from weakref import WeakKeyDictionary

from cattr import Converter
from msgpack import dumps, loads
from wrapt import decorator  # type: ignore

from .wire import Call

converter = Converter()

T = TypeVar("T")

RR = TypeVar("RR")
RT = TypeVar("RT")

RA1 = TypeVar("RA1")
RA2 = TypeVar("RA2")
RA3 = TypeVar("RA3")
RA4 = TypeVar("RA4")
RA5 = TypeVar("RA5")


class RpcCallable0(Generic[RT, RR]):
    def __call__(self: RT) -> Coroutine[Any, Any, RR]:
        pass


class RpcCallable1(Generic[RT, RA1, RR]):
    def __call__(self: RT, args: RA1) -> Coroutine[Any, Any, RR]:
        pass


class RpcCallable2(Generic[RT, RA1, RA2, RR]):
    def __call__(self: RT, arg1: RA1, arg2: RA2) -> Coroutine[Any, Any, RR]:
        pass


class RpcCallable3(Generic[RA1, RA2, RA3, RR]):
    def __call__(
        self, arg1: RA1, arg2: RA2, arg3: RA3
    ) -> Coroutine[Any, Any, RR]:
        pass


class RpcCallable4(Generic[RA1, RA2, RA3, RA4, RR]):
    def __call__(
        self, arg1: RA1, arg2: RA2, arg3: RA3, arg4: RA4
    ) -> Coroutine[Any, Any, RR]:
        pass


class RpcCallable5(Generic[RA1, RA2, RA3, RA4, RA5, RR]):
    def __call__(
        self, arg1: RA1, arg2: RA2, arg3: RA3, arg4: RA4, arg5: RA5
    ) -> Coroutine[Any, Any, RR]:
        pass


BT = TypeVar("BT")
R = TypeVar("R")
A1 = TypeVar("A1")
A2 = TypeVar("A2")
A3 = TypeVar("A3")
A4 = TypeVar("A4")
A5 = TypeVar("A5")


@overload
def rpc(func: Callable[[BT], Coroutine[Any, Any, R]]) -> RpcCallable0[BT, R]:
    ...


@overload
def rpc(
    func: Callable[[BT, A1], Coroutine[Any, Any, R]]
) -> RpcCallable1[BT, A1, R]:
    ...


@overload
def rpc(
    func: Callable[[BT, A1, A2], Coroutine[Any, Any, R]]
) -> RpcCallable2[BT, A1, A2, R]:
    ...


@overload
def rpc(
    func: Callable[[Any, A1, A2, A3], Coroutine[Any, Any, R]]
) -> RpcCallable3[A1, A2, A3, R]:
    ...


@overload
def rpc(
    func: Callable[[Any, A1, A2, A3, A4], Coroutine[Any, Any, R]]
) -> RpcCallable4[A1, A2, A3, A4, R]:
    ...


@overload
def rpc(
    func: Callable[[Any, A1, A2, A3, A4, A5], Coroutine[Any, Any, R]]
) -> RpcCallable5[A1, A2, A3, A4, A5, R]:
    ...


def rpc(func):
    func.__is_rpc = True  # type: ignore
    return func  # type: ignore


_clients: WeakKeyDictionary = WeakKeyDictionary()


async def create_client(
    api: Type[T], network_adapter: AsyncContextManager
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


def _adjust_rpc(coro, sender):
    argspec = getfullargspec(coro)
    return_type = argspec.annotations["return"]

    @decorator
    async def wrapper(wrapped, instance, args, kwargs):
        payload = dumps(converter.unstructure(Call(coro.__name__, args)))
        resp_payload = await sender(payload)
        return converter.structure(loads(resp_payload), return_type)

    return wrapper(coro)
