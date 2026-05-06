"""
Notification channels — Africa's Talking SMS + Twilio WhatsApp Business.

Environment variables:
  AT_API_KEY, AT_USERNAME          — Africa's Talking SMS
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM  — Twilio WhatsApp
"""
import asyncio
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Africa's Talking
AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_SMS_URL = (
    "https://api.sandbox.africastalking.com/version1/messaging"
    if AT_USERNAME == "sandbox"
    else "https://api.africastalking.com/version1/messaging"
)

# Twilio WhatsApp
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


async def send_sms(phone: str, message: str) -> dict:
    """
    Send SMS via Africa's Talking.

    Args:
        phone: Recipient in international format e.g. +254712345678
        message: Text body
    """
    headers = {"apiKey": AT_API_KEY, "Accept": "application/json"}
    data = {"username": AT_USERNAME, "to": phone, "message": message}

    async with httpx.AsyncClient() as client:
        resp = await client.post(AT_SMS_URL, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        result = resp.json()

    logger.info("SMS sent to %s", phone)
    return result


async def send_whatsapp(phone: str, message: str) -> dict:
    """
    Send WhatsApp message via Twilio.

    Args:
        phone: Recipient in format 2547XXXXXXXX (no '+')
        message: Message body
    """
    def _twilio_send():
        from twilio.rest import Client  # imported here to avoid startup crash if not installed
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            body=message,
            to=f"whatsapp:+{phone}",
        )
        return {"sid": msg.sid, "status": msg.status}

    result = await asyncio.to_thread(_twilio_send)
    logger.info("WhatsApp sent to %s", phone)
    return result


async def send_payout_notification(
    phone: str,
    farmer_name: str,
    payout_amount_kes: float,
    explanation_en: str,
    explanation_sw: str,
) -> None:
    """
    Send bilingual SMS + WhatsApp payout alert to farmer.

    The message structure:
      English: CropSure Alert: <explanation_en>. KES <amount> sent to your M-Pesa.
      Swahili: Onyo la CropSure: <explanation_sw>. KES <amount> imetumwa kwa M-Pesa yako.
    """
    amount_fmt = f"{payout_amount_kes:,.0f}"
    message = (
        f"CropSure Alert: {explanation_en} "
        f"KES {amount_fmt} sent to your M-Pesa.\n\n"
        f"Onyo la CropSure: {explanation_sw} "
        f"KES {amount_fmt} imetumwa kwa M-Pesa yako."
    )

    intl_phone = f"+{phone}"  # Africa's Talking expects +2547XXXXXXXX

    for label, coro in [
        ("SMS", send_sms(intl_phone, message)),
        ("WhatsApp", send_whatsapp(phone, message)),
    ]:
        try:
            await coro
        except Exception as exc:
            logger.error("%s notification to %s failed: %s", label, phone, exc)
