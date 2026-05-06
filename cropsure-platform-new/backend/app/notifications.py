"""SMS (Africa's Talking) and WhatsApp (Twilio) notifications."""

import logging
import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

AT_SMS_URL = "https://api.africastalking.com/version1/messaging"
AT_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"


async def send_sms(phone: str, message: str) -> dict:
    phone = phone.lstrip("+")
    if not phone.startswith("254"):
        phone = "254" + phone.lstrip("0")
    phone = f"+{phone}"

    if not settings.at_api_key or settings.at_username == "sandbox":
        logger.info("[SMS SANDBOX] To %s: %s", phone, message)
        return {"status": "sandbox", "phone": phone}

    url = AT_SMS_URL if settings.at_username != "sandbox" else AT_SANDBOX_URL
    async with httpx.AsyncClient() as c:
        r = await c.post(
            url,
            data={"username": settings.at_username, "to": phone, "message": message},
            headers={"apiKey": settings.at_api_key, "Accept": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


async def send_whatsapp(phone: str, message: str) -> dict:
    phone = phone.lstrip("+")
    if not phone.startswith("254"):
        phone = "254" + phone.lstrip("0")
    to = f"whatsapp:+{phone}"

    if not settings.twilio_account_sid:
        logger.info("[WHATSAPP SANDBOX] To %s: %s", to, message)
        return {"status": "sandbox", "to": to}

    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
            data={"From": settings.twilio_whatsapp_from, "To": to, "Body": message},
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


async def send_payout_notification(
    phone: str,
    farmer_name: str,
    amount_kes: float,
    explanation_en: str,
    explanation_sw: str,
) -> None:
    amount_fmt = f"KES {int(amount_kes):,}"
    sms = (
        f"CropSure Alert: {explanation_en} "
        f"{amount_fmt} sent to your M-Pesa. "
        f"Onyo la CropSure: {explanation_sw} "
        f"{amount_fmt} imetumwa kwa M-Pesa yako."
    )
    # SMS is the primary channel
    try:
        await send_sms(phone, sms)
    except Exception as e:
        logger.error("SMS send failed: %s", e)

    # WhatsApp secondary — same message
    try:
        await send_whatsapp(phone, sms)
    except Exception as e:
        logger.error("WhatsApp send failed: %s", e)


async def send_enrollment_confirmation(phone: str, farmer_name: str, policy_id: str, farm_id: str) -> None:
    msg = (
        f"Welcome to CropSure, {farmer_name}! Your farm is now insured. "
        f"Policy: {policy_id[:8].upper()}. "
        f"We will monitor your farm every 5 days using satellite data. "
        f"Karibu CropSure! Shamba lako sasa lina bima."
    )
    try:
        await send_sms(phone, msg)
    except Exception as e:
        logger.error("Enrollment SMS failed: %s", e)
