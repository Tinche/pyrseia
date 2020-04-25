# This file only exists to be type checked during a lint run.
from typing import Any

from aiohttp.web import Request

from pyrseia import NextMiddleware, server
from pyrseia.wire import Call

from ..calculator import Calculator


async def logging_middleware(
    ctx: Request, call: Call, next: NextMiddleware
) -> Any:
    print("Test")
    try:
        return await next(ctx, call)
    finally:
        print("Test 2")


serv = server(Calculator, ctx_cls=Request, middleware=[logging_middleware])


@serv.implement(Calculator.call_none)
async def call_none(ctx: Request) -> int:
    return 1
