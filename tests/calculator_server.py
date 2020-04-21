# This file only exists to be type checked during a lint run.
from pyrseia import server
from aiohttp.web import Request

from .calculator import Calculator

serv = server(Calculator, ctx_cls=Request)


@serv.implement(Calculator.call_none)
async def call_none(ctx: Request) -> int:
    return 1
