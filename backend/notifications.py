"""
Notification channels — Africa's Talking SMS + Meta WhatsApp Business Cloud API.

Environment variables required:
  SMS:       AT_API_KEY, AT_USERNAME
  WhatsApp:  WHATSAPP_TOKEN, WHATSAPP_PHONE_ID
"""
import os
import logging

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Africa's Talking
AT_API_KEY = os.getenv("AT_API_KEY", "")
AT_USERNAME = os.getenv("AT_USERNAME", "sandbox")
AT_SMS_URL = "https://api.africastalking.com/version1/messaging"

# Meta WhatsApp Business Cloud
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_URL = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"


async def send_sms(phone: str, message: str) -> dict:
    """
    Send an SMS via Africa's Talking.

    Args:
        phone: Recipient in international format e.g. +254712345678
        message: Text body (max 160 chars for single SMS)

    Returns:
        AT API response dict
    """
    headers = {
        "apiKey": AT_API_KEY,
        "Accept": "application/json",
    }
    data = {
        "username": AT_USERNAME,
        "to": phone,
        "message": message,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(AT_SMS_URL, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        result = resp.json()

    logger.info("SMS sent to %s: %s", phone, result)
    return result


async def send_whatsapp(phone: str, message: str) -> dict:
    """
    Send a WhatsApp text message via Meta Business Cloud API.

    Args:
        phone: Recipient in E.164 format without '+' e.g. 254712345678
        message: Message body

    Returns:
        Meta API response dict
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(WHATSAPP_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()

    logger.info("WhatsApp sent to %s: %s", phone, result)
    return result


async def notify_farmer(phone: str, message: str) -> None:
    """Send both SMS and WhatsApp. Logs failures without raising."""
    for label, coro in [("SMS", send_sms(phone, message)), ("WhatsApp", send_whatsapp(phone, message))]:
        try:
            await coro
        except Exception as exc:
            logger.error("%s notification to %s failed: %s", label, phone, exc)
