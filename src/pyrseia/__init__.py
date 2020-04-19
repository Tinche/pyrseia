from inspect import getfullargspec
from typing import (
    Any,
    Coroutine,
    Callable,
    Dict,
    Type,
    TypeVar,
    Generic,
    overload,
)

import attr

from cattr import Converter
from msgpack import dumps, loads
from wrapt import decorator  # type: ignore
from aiohttp import ClientSession

from .wire import Call

converter = Converter()

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


def client(url: str) -> Callable[[Type], Type]:
    def inner(cl: Type) -> Type:
        for name in dir(cl):
            obj = getattr(cl, name)
            if hasattr(obj, "__is_rpc"):
                setattr(cl, name, _adjust_rpc(obj, url))
        return cl

    return inner


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


def _adjust_rpc(coro, url: str):
    argspec = getfullargspec(coro)
    return_type = argspec.annotations["return"]

    @decorator
    async def wrapper(wrapped, instance, args, kwargs):
        payload = dumps(converter.unstructure(Call(coro.__name__, args)))
        async with ClientSession() as session:
            async with session.post(url, data=payload) as resp:
                resp_payload = await resp.read()
                return converter.structure(loads(resp_payload), return_type)

    return wrapper(coro)


SRA1 = TypeVar("SRA1")
SRA2 = TypeVar("SRA2")
SRA3 = TypeVar("SRA3")
SRA4 = TypeVar("SRA4")
SRA5 = TypeVar("SRA5")
SRR = TypeVar("SRR")

CT = TypeVar("CT")


@attr.s(slots=True)
class Server(Generic[CT]):
    _registry: Dict[str, Callable] = attr.ib(factory=dict, init=False)

    @overload
    def implement(
        self, c: RpcCallable0[CT, SRR]
    ) -> Callable[
        [Callable[[], Coroutine[Any, Any, SRR]]],
        Callable[[], Coroutine[Any, Any, SRR]],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable1[CT, SRA1, SRR]
    ) -> Callable[
        [Callable[[SRA1], Coroutine[Any, Any, SRR]]],
        Callable[[SRA1], Coroutine[Any, Any, SRR]],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable2[CT, SRA1, SRA2, SRR]
    ) -> Callable[
        [Callable[[SRA1, SRA2], Coroutine[Any, Any, SRR]]],
        Callable[[SRA1, SRA2], Coroutine[Any, Any, SRR]],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable3[SRA1, SRA2, SRA3, SRR]
    ) -> Callable[
        [Callable[[SRA1, SRA2, SRA3], Coroutine[Any, Any, SRR]]],
        Callable[[SRA1, SRA2, SRA3], Coroutine[Any, Any, SRR]],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable4[SRA1, SRA2, SRA3, SRA4, SRR]
    ) -> Callable[
        [Callable[[SRA1, SRA2, SRA3, SRA4], Coroutine[Any, Any, SRR]]],
        Callable[[SRA1, SRA2, SRA3, SRA4], Coroutine[Any, Any, SRR]],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable5[SRA1, SRA2, SRA3, SRA4, SRA5, SRR]
    ) -> Callable[
        [Callable[[SRA1, SRA2, SRA3, SRA4, SRA5], Coroutine[Any, Any, SRR]]],
        Callable[[SRA1, SRA2, SRA3, SRA4, SRA5], Coroutine[Any, Any, SRR]],
    ]:
        ...

    def implement(self, client_method):
        def wrapper(server_coro):
            self._registry[client_method.__name__] = server_coro
            return server_coro

        return wrapper

    async def process(self, payload: bytes) -> bytes:
        call = converter.structure(loads(payload), Call)
        handler = self._registry.get(call.name)
        if handler is None:
            raise ValueError("Handler not found.")
        res = await handler(*call.args)

        return dumps(converter.unstructure(res))


T = TypeVar("T")


def server(client: Type[T]) -> Server[T]:
    return Server()
