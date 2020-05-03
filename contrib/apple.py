from enum import Enum, IntEnum, unique
from typing import List, Optional

import attr
from aiohttp import ClientSession
from cattr import Converter
from pendulum import DateTime, from_timestamp
from ujson import dumps, loads

from pyrseia import create_client, rpc
from pyrseia.aiohttp import aiohttp_client_adapter
from pyrseia.wire import Call

PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"
SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
APP_STORE_CONVERTER = Converter()

APP_STORE_CONVERTER.register_structure_hook(
    DateTime, lambda m, _: from_timestamp(float(m) / 1000)
)


@attr.s(slots=True, frozen=True)
class ResponseBody:
    """This structure is called 'responseBody' by Apple."""

    @unique
    class Environment(str, Enum):
        SANDBOX = "Sandbox"
        PRODUCTION = "Production"

    @unique
    class Status(IntEnum):
        SUCCESS = 0
        INVALID_METHOD = 21000
        RETRY_TEMPORARY_ISSUE = 21002
        COULD_NOT_AUTHENTICATE = 21003
        INVALID_SHARED_SECRET = 21004
        RETRY_RECEIPT_SERVER_UNAVAILABLE = 21005
        RECEIPT_VALID_SUBSCRIPTION_EXPIRED = 21006
        SANDBOX_RECEIPT = 21007
        PRODUCTION_RECEIPT = 21008
        RETRY_INTERNAL_DATA_ACCESS = 21009
        USER_ACCOUNT_NOT_FOUND = 21010

    @attr.s(slots=True, frozen=True)
    class Receipt:
        @attr.s(slots=True, frozen=True)
        class InApp:
            @unique
            class CancellationReason(str, Enum):
                OTHER = "0"
                APP_ISSUE = "1"

            is_trial_period: str = attr.ib()
            original_purchase_date: str = attr.ib()
            original_purchase_date_ms: DateTime = attr.ib()
            original_purchase_date_pst: str = attr.ib()
            original_transaction_id: str = attr.ib()
            product_id: str = attr.ib()

            purchase_date: str = attr.ib()
            purchase_date_ms: DateTime = attr.ib()
            purchase_date_pst: str = attr.ib()
            quantity: int = attr.ib()
            transaction_id: str = attr.ib()

            cancellation_date: Optional[str] = attr.ib(default=None)
            cancellation_date_ms: Optional[DateTime] = attr.ib(default=None)
            cancellation_date_pst: Optional[str] = attr.ib(default=None)
            cancellation_reason: Optional[CancellationReason] = attr.ib(
                default=None
            )
            expires_date: Optional[str] = attr.ib(default=None)
            expires_date_ms: Optional[DateTime] = attr.ib(default=None)
            expires_date_pst: Optional[str] = attr.ib(default=None)
            is_in_intro_offer_period: Optional[str] = attr.ib(default=None)
            promotional_offer_id: Optional[str] = attr.ib(default=None)
            web_order_line_item_id: Optional[str] = attr.ib(default=None)

        class ReceiptType(str, Enum):
            PRODUCTION = "Production"
            PRODUCTION_VPP = "ProductionVPP"
            PRODUCTION_SANDBOX = "ProductionSandbox"
            PRODUCTION_VPP_SANDBOX = "ProductionVPPSandbox"

        app_item_id: int = attr.ib()
        application_version: str = attr.ib()
        bundle_id: str = attr.ib()
        download_id: int = attr.ib()

        in_app: List[InApp] = attr.ib()
        original_application_version: str = attr.ib()
        original_purchase_date: str = attr.ib()
        original_purchase_date_ms: DateTime = attr.ib()
        original_purchase_date_pst: str = attr.ib()
        receipt_creation_date: str = attr.ib()
        receipt_creation_date_ms: DateTime = attr.ib()
        receipt_creation_date_pst: str = attr.ib()
        receipt_type: ReceiptType = attr.ib()
        request_date: str = attr.ib()
        request_date_ms: DateTime = attr.ib()
        request_date_pst: str = attr.ib()
        version_external_identifier: int = attr.ib()
        expiration_date: Optional[str] = attr.ib(default=None)
        expiration_date_ms: Optional[DateTime] = attr.ib(default=None)
        expiration_date_pst: Optional[str] = attr.ib(default=None)
        preorder_date: Optional[str] = attr.ib(default=None)
        preorder_date_ms: Optional[DateTime] = attr.ib(default=None)
        preorder_date_pst: Optional[str] = attr.ib(default=None)

    @attr.s(slots=True, frozen=True)
    class LatestReceiptInfo:
        pass

    @attr.s(slots=True, frozen=True)
    class PendingRenewalInfo:
        pass

    status: Status = attr.ib()

    latest_receipt: Optional[str] = attr.ib(default=None)
    latest_receipt_info: List[LatestReceiptInfo] = attr.ib(factory=list)
    pending_renewal_info: List[PendingRenewalInfo] = attr.ib(factory=list)
    receipt: Optional[Receipt] = attr.ib(default=None)
    environment: Optional[Environment] = attr.ib(default=None)
    is_retryable: Optional[int] = attr.ib(default=None)


@attr.s(auto_exc=True, auto_attribs=True)
class HttpError(Exception):
    status_code: int


@attr.s(auto_exc=True)
class ParseError(Exception):
    """The app store response couldn't be parsed."""

    raw_response: bytes = attr.ib()


class AppStoreVerifier:
    @rpc
    async def verify_receipt(
        self,
        receipt_b64_data: str,
        password: Optional[str],
        exclude_old_transactions: bool,
    ) -> ResponseBody:
        ...


async def sender(session: ClientSession, call: Call, _) -> ResponseBody:
    payload = {"receipt-data": call.args[0]}
    if call.args[1] is not None:
        payload["password"] = call.args[1]
    if call.args[2]:
        payload["exclude-old-transactions"] = True
    async with session.post(
        PRODUCTION_URL,
        data=dumps(payload),
        headers={"content-type": "application/json"},
    ) as resp:
        if resp.status != 200:
            raise HttpError(resp.status)
        resp_payload = await resp.read()
        try:
            res = APP_STORE_CONVERTER.structure(
                loads(resp_payload), ResponseBody
            )
        except Exception as exc:
            raise ParseError(resp_payload) from exc

        return res


async def create_verifier():
    return await create_client(
        AppStoreVerifier, aiohttp_client_adapter("", 10, sender)
    )
