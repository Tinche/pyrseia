from typing import AsyncContextManager, Optional
from contextlib import asynccontextmanager

from httpx import AsyncClient


def httpx_client_adapter(
    url: str, timeout: Optional[int] = None
) -> AsyncContextManager:
    @asynccontextmanager
    async def adapter():

        async with AsyncClient(timeout=timeout) as client:

            async def sender(payload: bytes) -> bytes:
                res = await client.post(url, data=payload)
                return res.content

            yield sender

    return adapter()
