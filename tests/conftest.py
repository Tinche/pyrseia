from typing import Callable, TypeVar, Type
from pytest import fixture  # type: ignore
from pyrseia import server, Server

from .calculator import Calculator

C = TypeVar("C")


@fixture
def calculator_server_creator() -> Callable[[Type[C]], Server[Calculator, C]]:
    def create_server(ctx_cls: Type[C]) -> Server[Calculator, C]:
        serv: Server[Calculator, C] = server(Calculator, ctx_cls=ctx_cls)

        @serv.implement(Calculator.call_one)
        async def impl_test_call_one(i: int) -> int:
            return i

        @serv.implement(Calculator.add)
        async def add(a: int, b: int) -> int:
            return a + b

        @serv.implement(Calculator.multiply)
        async def multiply(a: int, b: int) -> int:
            return a * b

        return serv

    return create_server
