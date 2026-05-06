"""M-Pesa Daraja API — STK Push (C2B) and B2C payout."""

import base64
import logging
from datetime import datetime
from typing import Optional

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
BASE_URL = "https://sandbox.safaricom.co.ke" if settings.mpesa_sandbox else "https://api.safaricom.co.ke"


async def _get_token() -> str:
    if not settings.mpesa_consumer_key:
        return "SANDBOX_MOCK"
    creds = base64.b64encode(
        f"{settings.mpesa_consumer_key}:{settings.mpesa_consumer_secret}".encode()
    ).decode()
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {creds}"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()["access_token"]


def _normalise_phone(phone: str) -> str:
    phone = phone.lstrip("+").replace(" ", "")
    if phone.startswith("07") or phone.startswith("01"):
        phone = "254" + phone[1:]
    return phone


def _stk_password_and_ts() -> tuple:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    raw = f"{settings.mpesa_shortcode}{settings.mpesa_passkey}{ts}"
    return base64.b64encode(raw.encode()).decode(), ts


async def stk_push(phone: str, amount: float, account_ref: str, description: str) -> dict:
    token = await _get_token()
    phone = _normalise_phone(phone)
    pw, ts = _stk_password_and_ts()

    if not settings.mpesa_consumer_key:
        return {
            "CheckoutRequestID": f"mock-{account_ref[:8]}",
            "MerchantRequestID": "mock-merchant",
            "ResponseCode": "0",
            "simulated": True,
        }

    payload = {
        "BusinessShortCode": settings.mpesa_shortcode,
        "Password": pw, "Timestamp": ts,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone, "PartyB": settings.mpesa_shortcode,
        "PhoneNumber": phone,
        "CallBackURL": settings.mpesa_callback_url,
        "AccountReference": account_ref,
        "TransactionDesc": description,
    }
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30,
        )
        r.raise_for_status()
        return r.json()


async def b2c_payment(phone: str, amount: float, remarks: str) -> dict:
    token = await _get_token()
    phone = _normalise_phone(phone)

    if not settings.mpesa_consumer_key:
        return {
            "ConversationID": f"mock-conv-{phone[-4:]}",
            "ResponseCode": "0",
            "simulated": True,
        }

    payload = {
        "InitiatorName": settings.mpesa_initiator_name,
        "SecurityCredential": settings.mpesa_security_credential,
        "CommandID": "BusinessPayment",
        "Amount": int(amount), "PartyA": settings.mpesa_shortcode,
        "PartyB": phone, "Remarks": remarks,
        "QueueTimeOutURL": settings.mpesa_b2c_timeout_url,
        "ResultURL": settings.mpesa_b2c_result_url,
        "Occasion": "CropSurePayout",
    }
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{BASE_URL}/mpesa/b2c/v3/paymentrequest",
            json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30,
        )
        r.raise_for_status()
        return r.json()
