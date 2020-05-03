from functools import partial
from contextlib import asynccontextmanager
from typing import (
    AsyncContextManager,
    AsyncGenerator,
    Awaitable,
    Callable,
    Optional,
    Type,
    TypeVar,
)

from cattr import Converter
from httpx import AsyncClient
from msgpack import dumps, loads

from pyrseia.wire import Call

from . import ClientAdapter

converter = Converter()
T = TypeVar("T")


def httpx_client_adapter(
    url: str,
    timeout: Optional[int] = None,
    sender: Optional[
        Callable[[AsyncClient, Call, Type[T]], Awaitable[T]]
    ] = None,
) -> AsyncContextManager[ClientAdapter]:

    if sender is None:

        async def s(client, call: Call, resp_type: Type[T]) -> T:
            res = await client.post(
                url, data=dumps(converter.unstructure(call))
            )
            return converter.structure(loads(res.content), resp_type)

        sender = s

    @asynccontextmanager
    async def adapter() -> AsyncGenerator[ClientAdapter, None]:

        async with AsyncClient(timeout=timeout) as client:

            yield partial(s, client)

    return adapter()
