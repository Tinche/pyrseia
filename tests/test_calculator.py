from asyncio import Event, create_task

import pytest  # type: ignore
from aiohttp.web import AppRunner
from aiohttp.web import Request as AioRequest
from aiohttp.web import TCPSite
from hypercorn.asyncio import serve
from hypercorn.config import Config
from starlette.requests import Request as StarletteRequest

from pyrseia import Server, close_client, create_client
from pyrseia.aiohttp import aiohttp_client_adapter, create_aiohttp_app
from pyrseia.httpx import httpx_client_adapter
from pyrseia.starlette import create_starlette_app

from .calculator import Calculator


@pytest.mark.asyncio
async def test_aiohttp_aiohttp(
    unused_tcp_port: int, calculator_server_creator
) -> None:
    """Test the aiohttp client with the aiohttp app."""
    serv = calculator_server_creator(AioRequest)
    app = create_aiohttp_app(serv)

    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, port=unused_tcp_port)
    await site.start()

    t = await create_client(
        Calculator,
        aiohttp_client_adapter(f"http://localhost:{unused_tcp_port}"),
    )
    r = await t.add(1, 2)

    assert r == 3

    await runner.cleanup()
    await close_client(t)

    """Test the httpx client."""


@pytest.mark.asyncio
async def test_calling_httpx(
    unused_tcp_port: int, calculator_server_creator
) -> None:
    """Test the httpx client."""
    serv = calculator_server_creator(AioRequest)
    app = create_aiohttp_app(serv)

    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, port=unused_tcp_port)
    await site.start()

    t = await create_client(
        Calculator,
        httpx_client_adapter(f"http://localhost:{unused_tcp_port}", timeout=1),
    )
    r = await t.add(1, 2)

    assert r == 3

    await runner.cleanup()
    await close_client(t)


@pytest.mark.asyncio
async def test_httpx_starlette(
    unused_tcp_port: int, calculator_server_creator
) -> None:
    """Test the httpx client/starlette server combo."""
    serv: Server[Calculator, StarletteRequest] = calculator_server_creator(
        StarletteRequest
    )

    @serv.implement(Calculator.call_none)
    async def call_none(ctx: StarletteRequest) -> int:
        assert ctx.method == "POST"
        return 1

    app = create_starlette_app(serv)

    config = Config()
    config.bind = [f"localhost:{unused_tcp_port}"]
    shutdown_event = Event()

    async def shutdown_trigger():
        await shutdown_event.wait()

    task = create_task(serve(app, config, shutdown_trigger=shutdown_trigger))

    from asyncio import sleep

    await sleep(0.1)  # Wait for the server to start up.

    t = await create_client(
        Calculator,
        httpx_client_adapter(f"http://localhost:{unused_tcp_port}"),
    )
    r = await t.add(1, 2)
    await t.call_none()

    assert r == 3

    await close_client(t)

    shutdown_event.set()

    await task
