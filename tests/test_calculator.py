import pytest  # type: ignore
from aiohttp.web import (
    Application,
    AppRunner,
    Request,
    Response,
    TCPSite,
    post,
)

from .calculator import CalculatorRpc, serv


@pytest.mark.asyncio
async def test_calling() -> None:
    # Set up a server, on localhost.
    async def handler(request: Request) -> Response:
        resp = await serv.process(await request.read())
        return Response(body=resp)

    app = Application()
    app.add_routes([post("/", handler)])

    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, port=8000)
    await site.start()

    t = CalculatorRpc()
    r = await t.add(1, 2)

    assert r == 3

    await runner.cleanup()
