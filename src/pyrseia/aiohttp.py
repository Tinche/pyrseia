from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
    AsyncGenerator,
    Callable,
    Awaitable,
    Optional,
    Type,
    TypeVar,
)

from aiohttp import ClientSession, ClientTimeout
from aiohttp.web import Application, Request, Response, post
from cattr import Converter
from msgpack import dumps, loads
from functools import partial

from . import ClientAdapter
from ._server import Server
from .wire import Call

converter = Converter()

T = TypeVar("T")


def aiohttp_client_adapter(
    url: str,
    timeout: Optional[int] = None,
    sender: Optional[
        Callable[[ClientSession, Call, Type[T]], Awaitable[T]]
    ] = None,
) -> AsyncContextManager[ClientAdapter]:
    if sender is None:
        client_timeout = ClientTimeout(total=timeout)

        async def s(session, call, type):
            async with session.post(
                url,
                data=dumps(converter.unstructure(call)),
                timeout=client_timeout,
            ) as resp:
                return converter.structure(loads(await resp.read()), type)

    else:
        s = sender

    @asynccontextmanager
    async def aiohttp_adapter() -> AsyncGenerator[ClientAdapter, None]:
        session = ClientSession()

        try:
            yield partial(s, session)
        finally:
            await session.close()

    return aiohttp_adapter()


def create_aiohttp_app(
    serv: Server[Any, Request], route: str = "/"
) -> Application:
    def input_adapter(payload: bytes) -> Call:
        return converter.structure(loads(payload), Call)

    async def handler(request: Request) -> Response:
        call = input_adapter(await request.read())
        resp = await serv.process(call, request)
        return Response(body=dumps(converter.unstructure(resp)))

    app = Application()
    app.add_routes([post(route, handler)])

    return app
