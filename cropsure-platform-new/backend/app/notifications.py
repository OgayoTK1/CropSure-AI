"""SMS (Africa's Talking) and WhatsApp (Twilio) notifications."""

import logging
import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

AT_SMS_URL = "https://api.africastalking.com/version1/messaging"
AT_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"


# ── Phone normalisation ───────────────────────────────────────────────────────

def _e164(phone: str) -> str:
    """Convert Kenyan number to E.164 (+2547XXXXXXXX)."""
    p = phone.lstrip("+")
    if not p.startswith("254"):
        p = "254" + p.lstrip("0")
    return f"+{p}"


# ── Low-level send helpers ────────────────────────────────────────────────────

async def send_sms(phone: str, message: str) -> dict:
    e164 = _e164(phone)
    if not settings.at_api_key or settings.at_username == "sandbox":
        logger.info("[SMS SANDBOX] To %s: %s", e164, message)
        return {"status": "sandbox", "phone": e164}

    url = AT_SANDBOX_URL if settings.at_username == "sandbox" else AT_SMS_URL
    async with httpx.AsyncClient() as c:
        r = await c.post(
            url,
            data={"username": settings.at_username, "to": e164, "message": message},
            headers={"apiKey": settings.at_api_key, "Accept": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()


async def send_whatsapp(phone: str, message: str) -> dict:
    e164 = _e164(phone)
    to = f"whatsapp:{e164}"

    if not settings.twilio_account_sid:
        logger.info("[WHATSAPP SANDBOX] To %s:\n%s", to, message)
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


# ── NDVI mini bar chart ───────────────────────────────────────────────────────

def _ndvi_bar_chart(ndvi_series: list[float], baseline: float) -> str:
    """
    Build an ASCII bar chart of the last 6 NDVI readings for WhatsApp.

    Example output (8-char wide, 5-bar scale):
        NDVI Trend (last readings):
        Week -5: ████████ 0.68
        Week -4: ███████▌ 0.65
        Week -3: ██████   0.58
        Week -2: ████     0.42  ← stress zone
        Week -1: ██       0.31  ← TRIGGER
        Baseline:████████ 0.62
    """
    if not ndvi_series:
        return ""

    recent = ndvi_series[-6:]
    bars = "█▉▊▋▌▍▎▏"
    max_blocks = 8

    def _bar(v: float) -> str:
        clamped = max(0.0, min(1.0, v))
        total_eighths = round(clamped * max_blocks * 8)
        full = total_eighths // 8
        partial = total_eighths % 8
        bar = "█" * full
        if partial:
            bar += bars[8 - partial]
        return bar.ljust(max_blocks)

    lines = ["🛰 NDVI Trend (satellite readings):"]
    n = len(recent)
    for i, v in enumerate(recent):
        weeks_ago = n - i
        marker = " ⚠️" if v < baseline * 0.8 else ""
        label = "TRIGGER →" if i == n - 1 and v < baseline * 0.8 else f"Week -{weeks_ago}"
        lines.append(f"  {label}: {_bar(v)} {v:.2f}{marker}")
    lines.append(f"  Baseline: {_bar(baseline)} {baseline:.2f}")
    return "\n".join(lines)


# ── Notification functions ────────────────────────────────────────────────────

async def send_payout_notification(
    phone: str,
    farmer_name: str,
    amount_kes: float,
    explanation_en: str,
    explanation_sw: str,
    ndvi_series: list[float] | None = None,
    baseline_ndvi: float | None = None,
) -> None:
    """Send bilingual payout alert via SMS (primary) and WhatsApp (secondary with NDVI visual)."""
    amount_fmt = f"KES {int(amount_kes):,}"

    # SMS: concise bilingual message — keep under 160 chars
    sms = (
        f"CropSure: {explanation_en} "
        f"{amount_fmt} sent to your M-Pesa.\n"
        f"CropSure: {explanation_sw} "
        f"{amount_fmt} imetumwa kwa M-Pesa yako."
    )

    # WhatsApp: richer message with NDVI chart
    chart = ""
    if ndvi_series and baseline_ndvi:
        chart = "\n\n" + _ndvi_bar_chart(ndvi_series, baseline_ndvi)

    whatsapp_msg = (
        f"🌿 *CropSure AI — Payout Notification*\n\n"
        f"Habari {farmer_name},\n\n"
        f"*EN:* {explanation_en}\n"
        f"*SW:* {explanation_sw}\n\n"
        f"💸 *{amount_fmt}* imetumwa kwa M-Pesa yako.\n"
        f"💸 *{amount_fmt}* has been sent to your M-Pesa."
        f"{chart}\n\n"
        "Fungua app kwa maelezo zaidi / Open the app for more details:\n"
        "cropsure.ai"
    )

    try:
        await send_sms(phone, sms)
    except Exception as e:
        logger.error("SMS send failed for %s: %s", phone, e)

    try:
        await send_whatsapp(phone, whatsapp_msg)
    except Exception as e:
        logger.error("WhatsApp send failed for %s: %s", phone, e)


async def send_enrollment_confirmation(
    phone: str,
    farmer_name: str,
    policy_id: str,
    farm_id: str,
) -> None:
    """Send welcome SMS and WhatsApp on successful enrollment."""
    short_policy = policy_id[:8].upper()
    sms = (
        f"Karibu CropSure, {farmer_name}! Bima nambari: {short_policy}. "
        "Tutaangalia shamba lako kila siku 5 kutoka angani. "
        f"Welcome to CropSure! Policy: {short_policy}. "
        "Your farm is monitored every 5 days from space."
    )
    whatsapp_msg = (
        f"🌱 *Karibu CropSure AI, {farmer_name}!*\n\n"
        f"Shamba lako sasa lina bima.\n"
        f"*Nambari ya Bima / Policy:* `{short_policy}`\n\n"
        "Tutafuatilia shamba lako kwa setilaiti kila siku 5.\n"
        "We will monitor your farm by satellite every 5 days.\n\n"
        "Ukipata tatizo lolote, tutakutumia ujumbe moja kwa moja.\n"
        "If stress is detected, you will receive a payout automatically."
    )

    try:
        await send_sms(phone, sms)
    except Exception as e:
        logger.error("Enrollment SMS failed for %s: %s", phone, e)

    try:
        await send_whatsapp(phone, whatsapp_msg)
    except Exception as e:
        logger.error("Enrollment WhatsApp failed for %s: %s", phone, e)
