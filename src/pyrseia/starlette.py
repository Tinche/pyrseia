from typing import Any, TypeVar

from cattr import Converter
from msgpack import dumps, loads
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from ._server import Server
from .wire import Call

T = TypeVar("T")
converter = Converter()


def create_starlette_app(
    serv: Server[Any, Request], route: str = "/", debug=False, method="POST"
) -> Starlette:
    def input_adapter(payload: bytes) -> Call:
        return converter.structure(loads(payload), Call)

    async def handler(request: Request):
        payload = await request.body()

        resp = await serv.process(input_adapter(payload), request)

        return Response(dumps(converter.unstructure(resp)))

    app = Starlette(
        debug=debug, routes=[Route(route, handler, methods=[method])]
    )

    return app
