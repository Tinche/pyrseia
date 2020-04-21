from typing import Optional

from pyrseia import rpc


class Calculator:
    @rpc
    async def call_none(self) -> int:
        ...

    @rpc
    async def call_one(self, i: int) -> int:
        ...

    @rpc
    async def add(self, a: int, b: int) -> int:
        ...

    @rpc
    async def multiply(self, a: int, b: int) -> int:
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


class Calc2Rpc:
    @rpc
    async def add(self, a: int, b: int) -> int:
        ...
