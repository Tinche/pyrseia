from contextlib import asynccontextmanager
from typing import Any, AsyncContextManager, AsyncGenerator, Optional

from aiohttp import ClientSession, ClientTimeout
from aiohttp.web import Application, Request, Response, post
from cattr import Converter
from msgpack import dumps, loads

from . import ClientAdapter
from ._server import Server
from .wire import Call

converter = Converter()


def aiohttp_client_adapter(
    url: str, timeout: Optional[int] = None, method="POST"
) -> AsyncContextManager[ClientAdapter]:
    @asynccontextmanager
    async def aiohttp_adapter() -> AsyncGenerator[ClientAdapter, None]:
        session = ClientSession()
        client_timeout = ClientTimeout(total=timeout)
        req_method = getattr(session, method.lower())

        async def client_sender(payload: bytes) -> bytes:
            async with req_method(
                url, data=payload, timeout=client_timeout
            ) as resp:
                return await resp.read()

        try:
            yield client_sender
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
