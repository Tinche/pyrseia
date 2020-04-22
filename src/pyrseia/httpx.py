from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator, Optional

from httpx import AsyncClient

from . import ClientAdapter


def httpx_client_adapter(
    url: str, timeout: Optional[int] = None
) -> AsyncContextManager[ClientAdapter]:
    @asynccontextmanager
    async def adapter() -> AsyncGenerator[ClientAdapter, None]:

        async with AsyncClient(timeout=timeout) as client:

            async def sender(payload: bytes) -> bytes:
                res = await client.post(url, data=payload)
                return res.content

            yield sender

    return adapter()
