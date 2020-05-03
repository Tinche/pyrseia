from inspect import getfullargspec
from typing import (
    Any,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    overload,
)

import attr
from wrapt import decorator  # type: ignore

from ._api import (
    RpcCallable0,
    RpcCallable1,
    RpcCallable2,
    RpcCallable3,
    RpcCallable4,
    RpcCallable5,
)
from .wire import Call

CT = TypeVar("CT")
CTXT = TypeVar("CTXT")

SRA1 = TypeVar("SRA1")
SRA2 = TypeVar("SRA2")
SRA3 = TypeVar("SRA3")
SRA4 = TypeVar("SRA4")
SRA5 = TypeVar("SRA5")
SRR = TypeVar("SRR")

IT = TypeVar("IT")
ServerInputAdapter = Callable[[IT], Call]
ServerOutputAdapter = Callable[[Any], Awaitable]
NextMiddleware = Callable[[CTXT, Call], Awaitable[Any]]
Middleware = Callable[[CTXT, Call, NextMiddleware[CTXT]], Any]


@attr.s(slots=True, frozen=True)
class Server(Generic[CT, CTXT]):
    _registry: Dict[str, Callable] = attr.ib(factory=dict, init=False)
    _middleware: Sequence[Middleware] = attr.ib(factory=list)
    _middleware_chain: Optional[
        Callable[[CTXT, Call], Awaitable[Any]]
    ] = attr.ib(init=False, repr=False, default=None)

    def __attrs_post_init__(self):
        if self._middleware:

            async def next_call(req_ctx, call):
                handler = self._registry[call.name]
                return await handler(req_ctx, *call.args)

            n = next_call

            for mid in reversed(self._middleware):

                async def next_call(req_ctx, call, _n=n, middleware=mid):  # type: ignore
                    return await middleware(req_ctx, call, _n)

                n = next_call
            object.__setattr__(self, "_middleware_chain", n)

    @overload
    def implement(
        self, c: RpcCallable0[CT, SRR]
    ) -> Callable[
        [
            Union[
                Callable[[], Coroutine[Any, Any, SRR]],
                Callable[[CTXT], Coroutine[Any, Any, SRR]],
            ],
        ],
        Union[
            Callable[[], Coroutine[Any, Any, SRR]],
            Callable[[CTXT], Coroutine[Any, Any, SRR]],
        ],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable1[CT, SRA1, SRR]
    ) -> Callable[
        [
            Union[
                Callable[[SRA1], Coroutine[Any, Any, SRR]],
                Callable[[CTXT, SRA1], Coroutine[Any, Any, SRR]],
            ]
        ],
        Union[
            Callable[[SRA1], Coroutine[Any, Any, SRR]],
            Callable[[CTXT, SRA1], Coroutine[Any, Any, SRR]],
        ],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable2[CT, SRA1, SRA2, SRR]
    ) -> Callable[
        [
            Union[
                Callable[[SRA1, SRA2], Coroutine[Any, Any, SRR]],
                Callable[[CTXT, SRA1, SRA2], Coroutine[Any, Any, SRR]],
            ]
        ],
        Union[
            Callable[[SRA1, SRA2], Coroutine[Any, Any, SRR]],
            Callable[[CTXT, SRA1, SRA2], Coroutine[Any, Any, SRR]],
        ],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable3[SRA1, SRA2, SRA3, SRR]
    ) -> Callable[
        [
            Union[
                Callable[[SRA1, SRA2, SRA3], Coroutine[Any, Any, SRR]],
                Callable[[CTXT, SRA1, SRA2, SRA3], Coroutine[Any, Any, SRR]],
            ]
        ],
        Union[
            Callable[[SRA1, SRA2, SRA3], Coroutine[Any, Any, SRR]],
            Callable[[CTXT, SRA1, SRA2, SRA3], Coroutine[Any, Any, SRR]],
        ],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable4[SRA1, SRA2, SRA3, SRA4, SRR]
    ) -> Callable[
        [
            Union[
                Callable[[SRA1, SRA2, SRA3, SRA4], Coroutine[Any, Any, SRR]],
                Callable[
                    [CTXT, SRA1, SRA2, SRA3, SRA4], Coroutine[Any, Any, SRR]
                ],
            ]
        ],
        Union[
            Callable[[SRA1, SRA2, SRA3, SRA4], Coroutine[Any, Any, SRR]],
            Callable[[CTXT, SRA1, SRA2, SRA3, SRA4], Coroutine[Any, Any, SRR]],
        ],
    ]:
        ...

    @overload
    def implement(
        self, c: RpcCallable5[SRA1, SRA2, SRA3, SRA4, SRA5, SRR]
    ) -> Callable[
        [
            Union[
                Callable[
                    [SRA1, SRA2, SRA3, SRA4, SRA5], Coroutine[Any, Any, SRR]
                ],
                Callable[
                    [CTXT, SRA1, SRA2, SRA3, SRA4, SRA5],
                    Coroutine[Any, Any, SRR],
                ],
            ]
        ],
        Union[
            Callable[[SRA1, SRA2, SRA3, SRA4, SRA5], Coroutine[Any, Any, SRR]],
            Callable[
                [CTXT, SRA1, SRA2, SRA3, SRA4, SRA5], Coroutine[Any, Any, SRR]
            ],
        ],
    ]:
        ...

    def implement(self, client_method):
        def wrapper(server_coro):
            c = getfullargspec(client_method)
            s = getfullargspec(server_coro)
            # Server args might include the context, but the client args
            # include the 'self'.
            if len(s.args) < len(c.args):
                # We're *not* injecting the request context as the first arg.
                @decorator
                async def ctx_wrapper(wrapper, instance, args, kwargs):
                    return await wrapper(*args[1:], **kwargs)

                server_coro = ctx_wrapper(server_coro)
            self._registry[client_method.__name__] = server_coro
            return server_coro

        return wrapper

    async def process(self, call: Call, req_ctx: CTXT) -> Any:
        handler = self._registry.get(call.name)
        if handler is None:
            raise ValueError("Handler not found.")

        if self._middleware_chain is not None:
            res = await self._middleware_chain(req_ctx, call)
        else:
            res = await handler(req_ctx, *call.args)

        return res


T = TypeVar("T")


def server(
    client: Type[T],
    ctx_cls: Union[Type[CTXT], Type[None]] = type(None),
    *,
    middleware: List[Middleware[CTXT]] = [],
) -> Server[T, CTXT]:
    return Server(middleware=middleware)
