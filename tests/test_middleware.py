from asyncio import create_task, sleep
from typing import Any

import pytest  # type: ignore
from attr import evolve

from pyrseia.wire import Call

from .calculator import Calculator


@pytest.mark.asyncio
async def test_logging_middleware(calculator_server_creator) -> None:
    """Create a logging middleware, and test it out."""
    logs = []

    async def logging_middleware(ctx, call: Call, next):
        logs.append(f"BEFORE {call.name}")
        try:
            return await next(ctx, call)
        finally:
            logs.append(f"AFTER {call.name}")

    serv = calculator_server_creator(
        Calculator, middleware=[logging_middleware]
    )

    @serv.implement(Calculator.call_none)
    async def call_none() -> int:
        await sleep(0.1)
        return 1

    @serv.implement(Calculator.call_one)
    async def call_one(i: int) -> int:
        await sleep(0.1)
        return i

    t0 = create_task(serv.process(Call("call_one", (1,)), None))
    await sleep(0.01)
    resp = await serv.process(Call("call_none", ()), None)

    await t0

    assert resp == 1

    assert logs == [
        "BEFORE call_one",
        "BEFORE call_none",
        "AFTER call_one",
        "AFTER call_none",
    ]


@pytest.mark.asyncio
async def test_ctx_mutating_middleware(calculator_server_creator) -> None:
    """Create a call and/or context mutating middleware."""

    async def call_one_middleware(ctx, call: Call, next) -> Any:
        """This middleware mutates the argument to call_one."""
        if call.name == "call_one":
            call = evolve(call, args=(call.args[0] + 1,))
        return await next(ctx, call)

    async def call_none_middleware(ctx, call: Call, next) -> Any:
        """This middleware mutates the result of call_none."""
        res = await next(ctx, call)
        if call.name == "call_none":
            res += 1
        return res

    serv = calculator_server_creator(
        Calculator, middleware=[call_one_middleware, call_none_middleware]
    )

    @serv.implement(Calculator.call_none)
    async def call_none() -> int:
        await sleep(0.1)
        return 1

    @serv.implement(Calculator.call_one)
    async def call_one(i: int) -> int:
        await sleep(0.1)
        return i

    call_one_task = create_task(serv.process(Call("call_one", (1,)), None))
    await sleep(0.01)
    call_none_resp = await serv.process(Call("call_none", ()), None)

    await call_one_task

    assert call_none_resp == 2
    assert call_one_task.result() == 2
