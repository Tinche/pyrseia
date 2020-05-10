"""Google services."""
from asyncio import create_task
from enum import IntEnum, unique
from typing import AsyncContextManager, List, Optional, Type, TypeVar

import attr
from aiohttp import ClientSession
from cattr import Converter
from jwt import encode
from pendulum import DateTime, from_timestamp
from ujson import loads

from pyrseia import ClientAdapter, create_client, rpc
from pyrseia.aiohttp import aiohttp_client_adapter
from pyrseia.wire import Call

# Scope for purchases: https://www.googleapis.com/auth/androidpublisher
BASE_URL = "https://www.googleapis.com/androidpublisher/v3/applications"
ACCESS_TOKEN_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
SCOPE_ANDROIDPUBLISHER = "https://www.googleapis.com/auth/androidpublisher"
converter = Converter()


@attr.s(auto_attribs=True)
class ServiceAccountCredentials:
    project_id: str
    auth_uri: str
    token_uri: str
    client_email: str
    private_key: str

    @classmethod
    def from_filename(cls, filename: str):
        with open(filename) as f:
            return converter.structure(loads(f.read()), cls)


@attr.s(auto_exc=True, auto_attribs=True)
class HttpError(Exception):
    status_code: int
    response_payload: bytes


@attr.s(auto_exc=True, auto_attribs=True)
class ParseError(Exception):
    payload: bytes


@attr.s(slots=True, frozen=True)
class ProductPurchase:
    @unique
    class AcknowledgementState(IntEnum):
        NOT_ACKED = 0
        ACKED = 1

    @unique
    class ConsumptionState(IntEnum):
        NOT_CONSUMED = 0
        CONSUMED = 1

    @unique
    class PurchaseState(IntEnum):
        PURCHASED = 0
        CANCELED = 1
        PENDING = 2

    @unique
    class PurchaseType(IntEnum):
        TEST = 0
        PROMO = 1
        REWARDED = 2

    kind: str = attr.ib()
    acknowledgementState: AcknowledgementState = attr.ib()
    consumptionState: ConsumptionState = attr.ib()
    developerPayload: str = attr.ib()
    orderId: str = attr.ib()
    purchaseState: PurchaseState = attr.ib()
    purchaseTimeMillis: int = attr.ib()
    purchaseType: Optional[PurchaseType] = attr.ib(default=None)


@attr.s(slots=True, frozen=True)
class VoidedPurchase:
    @unique
    class VoidedSource(IntEnum):
        USER = 0
        DEVELOPER = 1
        GOOGLE = 2

    @unique
    class VoidedReason(IntEnum):
        OTHER = 0
        REMORSE = 1
        NOT_RECEIVED = 2
        DEFECTIVE = 3
        ACCIDENTAL_PURCHASE = 4
        FRAUD = 5
        FRIENDLY_FRAUD = 6
        CHARGEBACK = 7

    kind: str = attr.ib()
    purchaseToken: str = attr.ib()
    purchaseTimeMillis: str = attr.ib()
    voidedTimeMillis: str = attr.ib()
    orderId: str = attr.ib()
    voidedSource: VoidedSource = attr.ib()
    voidedReason: VoidedReason = attr.ib()

    @property
    def purchase_time(self) -> DateTime:
        return from_timestamp(float(self.purchaseTimeMillis) / 1000)

    @property
    def voided_time(self) -> DateTime:
        return from_timestamp(float(self.voidedTimeMillis) / 1000)


@attr.s(slots=True, frozen=True)
class VoidedPurchasesResponse:
    @attr.s(slots=True, frozen=True)
    class TokenPagination:
        nextPageToken: str = attr.ib()

    voidedPurchases: List[VoidedPurchase] = attr.ib()
    tokenPagination: Optional[TokenPagination] = attr.ib(default=None)


class GooglePlayDeveloperApi:
    @rpc
    async def get_purchases_products(
        self, package_name: str, product_id: str, token: str
    ) -> ProductPurchase:
        ...

    @rpc
    async def get_voided_purchases(
        self,
        package_name: str,
        start_time: Optional[int],
        end_time: Optional[int],
        token: Optional[str],
        type: int,
    ) -> VoidedPurchasesResponse:
        ...


@attr.s(auto_attribs=True, slots=True, frozen=True)
class AccessToken:
    access_token: str
    token_type: str
    expires_in: int


async def request_access_token(
    session: ClientSession,
    url: str,
    creds: ServiceAccountCredentials,
    now: Optional[DateTime] = None,
) -> AccessToken:
    now = now or DateTime.utcnow()
    assertion = encode(
        {
            "iss": creds.client_email,
            "scope": SCOPE_ANDROIDPUBLISHER,
            "aud": creds.token_uri,
            "iat": int(now.timestamp()),
            "exp": int(now.add(hours=1).timestamp()),
        },
        creds.private_key,
        algorithm="RS256",
    ).decode("utf8")

    async with session.post(
        url,
        data={"grant_type": ACCESS_TOKEN_GRANT_TYPE, "assertion": assertion},
    ) as resp:
        payload = await resp.read()
        if resp.status != 200:
            raise HttpError(resp.status, payload)
        return converter.structure(loads(payload), AccessToken)


async def invoke_api(session: ClientSession, token: str, url: str) -> bytes:
    async with session.get(
        url, headers={"Authorization": f"Bearer {token}"}
    ) as resp:
        resp_payload = await resp.read()
        if resp.status != 200:
            raise HttpError(resp.status, resp_payload)
        return resp_payload


T = TypeVar("T")


def google_client_network_adapter(
    creds: ServiceAccountCredentials,
) -> AsyncContextManager[ClientAdapter]:
    token = None
    task = None

    async def sender(
        session: ClientSession, call: Call, resp_type: Type[T]
    ) -> T:
        nonlocal task, token
        if token is None:
            created_task = False
            if task is None:
                created_task = True
                task = create_task(
                    request_access_token(session, creds.token_uri, creds)
                )
            local_task = task  # 'task' will get cleaned up eventually.
            await local_task
            token = local_task.result()
            if created_task:
                task = None

        if call.name == "get_purchases_products":
            url = f"{BASE_URL}/{call.args[0]}/purchases/products/{call.args[1]}/tokens/{call.args[2]}"
        elif call.name == "get_voided_purchases":
            url = f"{BASE_URL}/{call.args[0]}/purchases/voidedpurchases"
        try:
            resp = await invoke_api(session, token.access_token, url)
        except HttpError as exc:
            if exc.status_code == 401:
                # Refresh the access token.
                if task is not None:
                    local_task = task
                    await local_task
                    local_token = local_task.result()
                else:
                    task = create_task(
                        request_access_token(session, creds.token_uri, creds)
                    )
                    await task
                    local_token = token = task.result()
                    task = None
                resp = await invoke_api(session, local_token.access_token, url)
            else:
                raise

        try:
            return converter.structure(loads(resp), resp_type)
        except Exception as exc:
            raise ParseError(resp) from exc

    return aiohttp_client_adapter("", sender=sender)


async def create_google_client():
    return await create_client(
        GooglePlayDeveloperApi,
        google_client_network_adapter(
            ServiceAccountCredentials.from_filename("service.json")
        ),
    )
