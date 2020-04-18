from typing import Optional

from pyrseia import client, rpc, server


@client("http://localhost:8000")
class CalculatorRpc:
    @rpc
    async def call_none(self) -> None:
        ...

    @rpc
    async def call_one(self, i: int) -> int:
        ...

    @rpc
    async def add(self, a: int, b: int) -> int:
        ...

    @rpc
    async def call_three(self, i: int, s: str, f: float) -> float:
        ...

    @rpc
    async def call_four(self, i: int, s: str, f: float, b: bytes) -> bytes:
        ...

    @rpc
    async def call_five(
        self, i: int, s: str, f: float, b: bytes, os: Optional[str]
    ) -> Optional[str]:
        ...

    async def non_rpc(self, i: int) -> int:
        return 1


serv = server(CalculatorRpc)


@serv.implement(CalculatorRpc.call_one)
async def impl_test_call_one(i: int) -> int:
    return i


@serv.implement(CalculatorRpc.add)
async def add(a: int, b: int) -> int:
    return a + b
