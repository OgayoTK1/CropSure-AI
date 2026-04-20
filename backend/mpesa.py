"""
Safaricom Daraja API — STK Push (premium collection) + B2C (drought payouts).
Docs: https://developer.safaricom.co.ke/
"""
import base64
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()

CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY", "")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET", "")
SHORTCODE = os.getenv("MPESA_SHORTCODE", "174379")          # default: Daraja sandbox
PASSKEY = os.getenv("MPESA_PASSKEY", "")
B2C_INITIATOR_NAME = os.getenv("MPESA_B2C_INITIATOR_NAME", "")
B2C_SECURITY_CREDENTIAL = os.getenv("MPESA_B2C_SECURITY_CREDENTIAL", "")
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "https://example.com/webhooks/stk-callback")
B2C_RESULT_URL = os.getenv("MPESA_B2C_RESULT_URL", "https://example.com/webhooks/b2c-result")
B2C_TIMEOUT_URL = os.getenv("MPESA_B2C_TIMEOUT_URL", "https://example.com/webhooks/b2c-timeout")
ENVIRONMENT = os.getenv("MPESA_ENVIRONMENT", "sandbox")  # sandbox or production

BASE_URL = (
    "https://sandbox.safaricom.co.ke"
    if ENVIRONMENT == "sandbox"
    else "https://api.safaricom.co.ke"
)


async def _get_access_token() -> str:
    credentials = base64.b64encode(f"{CONSUMER_KEY}:{CONSUMER_SECRET}".encode()).decode()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


def _stk_password() -> tuple[str, str]:
    """Returns (password, timestamp) for STK push."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{SHORTCODE}{PASSKEY}{timestamp}"
    password = base64.b64encode(raw.encode()).decode()
    return password, timestamp


async def stk_push(phone: str, amount: int, account_ref: str, description: str) -> dict:
    """
    Initiate an STK Push to collect a premium payment from a farmer.

    Args:
        phone: Farmer phone in format 2547XXXXXXXX
        amount: Amount in KES (integer)
        account_ref: e.g. farm ID or policy number
        description: Short transaction description

    Returns:
        Daraja API response dict (includes CheckoutRequestID, MerchantRequestID)
    """
    token = await _get_access_token()
    password, timestamp = _stk_password()

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": account_ref,
        "TransactionDesc": description,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


async def b2c_payment(phone: str, amount: int, remarks: str) -> dict:
    """
    Initiate a B2C payout to a farmer on drought detection.

    Args:
        phone: Farmer phone in format 2547XXXXXXXX
        amount: Payout amount in KES (integer)
        remarks: Short description e.g. "Drought payout - Farm XYZ"

    Returns:
        Daraja API response dict (includes ConversationID, OriginatorConversationID)
    """
    token = await _get_access_token()

    payload = {
        "InitiatorName": B2C_INITIATOR_NAME,
        "SecurityCredential": B2C_SECURITY_CREDENTIAL,
        "CommandID": "BusinessPayment",
        "Amount": amount,
        "PartyA": SHORTCODE,
        "PartyB": phone,
        "Remarks": remarks,
        "QueueTimeOutURL": B2C_TIMEOUT_URL,
        "ResultURL": B2C_RESULT_URL,
        "Occassion": "",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/mpesa/b2c/v1/paymentrequest",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
