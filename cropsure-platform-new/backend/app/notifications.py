"""
CropSure AI — Farmer Notification Service

Three outbound channels:
  1. SMS  (Africa's Talking)   — primary, works on any phone
  2. WhatsApp (Twilio)          — richer, includes NDVI chart and agronomic advice
  3. Both fire together on every significant event

Events:
  • Enrollment confirmation   → welcome + policy number
  • Farm progress update       → every satellite pass (healthy or mild stress)
  • Early warning              → NDVI dropping but not yet trigger threshold
  • Payout notification        → stress confirmed, M-Pesa sent
"""

import logging
from typing import Optional

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

AT_SMS_URL = "https://api.africastalking.com/version1/messaging"
AT_SANDBOX_URL = "https://api.sandbox.africastalking.com/version1/messaging"


# ── Agronomic advice library ─────────────────────────────────────────────────
# Bilingual, actionable, farmer-appropriate advice for each stress condition.

AGRONOMIC_ADVICE = {
    "drought": {
        "en": (
            "💧 *Drought Safety Measures:*\n"
            "1. Apply mulch (grass/straw) around crop base to retain soil moisture.\n"
            "2. Water in early morning or evening — never midday.\n"
            "3. Remove all weeds immediately — they compete for water.\n"
            "4. If you have irrigation, use it now.\n"
            "5. Contact your nearest agricultural extension officer for emergency seed support."
        ),
        "sw": (
            "💧 *Hatua za Usalama - Ukame:*\n"
            "1. Weka matandazo (nyasi/majani) karibu na mizizi kuhifadhi unyevu.\n"
            "2. Mwagilia asubuhi mapema au jioni — si mchana.\n"
            "3. Ondoa magugu yote mara moja — yanashindana na maji.\n"
            "4. Ikiwa una umwagiliaji, uitumie sasa hivi.\n"
            "5. Wasiliana na afisa wa kilimo wa karibu nawe kwa msaada wa dharura."
        ),
    },
    "flood": {
        "en": (
            "🌊 *Flood Safety Measures:*\n"
            "1. Clear all drainage channels immediately to remove standing water.\n"
            "2. Do NOT walk on waterlogged soil — it damages roots.\n"
            "3. Watch leaves closely for yellow spots (fungal disease sign).\n"
            "4. If leaves turn yellow, apply fungicide within 48 hours.\n"
            "5. Document all crop damage with photos for insurance records."
        ),
        "sw": (
            "🌊 *Hatua za Usalama - Mafuriko:*\n"
            "1. Safisha mifereji yote ya maji mara moja kuondoa maji yaliyosimama.\n"
            "2. USITEMBEE kwenye udongo uliojaa maji — unaharibu mizizi.\n"
            "3. Angalia majani kwa makini kwa madoa ya njano (dalili ya ugonjwa wa ukungu).\n"
            "4. Ikiwa majani yanageuka njano, nyunyizia dawa ya ukungu ndani ya masaa 48.\n"
            "5. Piga picha za uharibifu wote kwa kumbukumbu za bima."
        ),
    },
    "pest_disease": {
        "en": (
            "🐛 *Pest & Disease Safety Measures:*\n"
            "1. Walk your farm section by section — look for holes, webbing, or discolouration.\n"
            "2. Remove and destroy infected plants immediately before it spreads.\n"
            "3. Contact your agro-dealer today for the correct pesticide.\n"
            "4. Apply pesticide in cool morning hours for best effectiveness.\n"
            "5. Do not work in infected areas then healthy areas — you will spread disease."
        ),
        "sw": (
            "🐛 *Hatua za Usalama - Wadudu/Magonjwa:*\n"
            "1. Tembea shamba lako sehemu kwa sehemu — tafuta mashimo, utando, au mabadiliko ya rangi.\n"
            "2. Ondoa na haribu mimea iliyoathirika mara moja kabla haijasambaa.\n"
            "3. Wasiliana na muuzaji wako wa kilimo leo kwa dawa sahihi.\n"
            "4. Nyunyizia dawa asubuhi mapema wakati wa baridi kwa ufanisi zaidi.\n"
            "5. Usifanye kazi katika maeneo yaliyoathirika kisha maeneo mazuri — utasambaza ugonjwa."
        ),
    },
    "mild_stress": {
        "en": (
            "⚠️ *Early Warning — Act Now:*\n"
            "1. Check your soil moisture today — push a finger 5cm into soil.\n"
            "   Dry? Irrigate immediately. Moist? Monitor closely.\n"
            "2. Apply top-dressing fertiliser if plant growth looks slow.\n"
            "3. Remove weeds that may be competing for nutrients.\n"
            "4. Monitor your farm daily for the next 7 days.\n"
            "5. If conditions worsen, call your extension officer."
        ),
        "sw": (
            "⚠️ *Onyo la Awali — Chukua Hatua Sasa:*\n"
            "1. Angalia unyevu wa udongo leo — ingiza kidole sm 5 ardhini.\n"
            "   Kame? Mwagilia mara moja. Na unyevu? Fuatilia kwa makini.\n"
            "2. Weka mbolea ya nyongeza ikiwa ukuaji wa mmea unaonekana wa polepole.\n"
            "3. Ondoa magugu yanayoshindana na virutubisho.\n"
            "4. Fuatilia shamba lako kila siku kwa siku 7 zijazo.\n"
            "5. Ikiwa hali inazidi kuwa mbaya, piga simu afisa wako wa kilimo."
        ),
    },
    "healthy": {
        "en": (
            "✅ *Farm Management Tips:*\n"
            "1. Continue regular weeding every 2 weeks.\n"
            "2. Check if crops need second fertiliser dressing (mid-season).\n"
            "3. Prepare your harvest equipment and storage space in advance.\n"
            "4. Keep your CropSure policy active for next season."
        ),
        "sw": (
            "✅ *Vidokezo vya Usimamizi wa Shamba:*\n"
            "1. Endelea kupalilia kila wiki mbili.\n"
            "2. Angalia ikiwa mazao yanahitaji mbolea ya pili (katikati ya msimu).\n"
            "3. Andaa vifaa vya mavuno na nafasi ya kuhifadhi mapema.\n"
            "4. Weka bima yako ya CropSure hai kwa msimu ujao."
        ),
    },
}


def _advice(stress_type: str, lang: str = "en") -> str:
    key = stress_type if stress_type in AGRONOMIC_ADVICE else "healthy"
    return AGRONOMIC_ADVICE[key][lang]


# ── Phone normalisation ───────────────────────────────────────────────────────

def _e164(phone: str) -> str:
    p = phone.lstrip("+")
    if not p.startswith("254"):
        p = "254" + p.lstrip("0")
    return f"+{p}"


# ── Low-level send ────────────────────────────────────────────────────────────

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


# ── NDVI ASCII bar chart ──────────────────────────────────────────────────────

def _ndvi_bar(value: float, max_blocks: int = 8) -> str:
    blocks = "█▉▊▋▌▍▎▏"
    clamped = max(0.0, min(1.0, value))
    total_eighths = round(clamped * max_blocks * 8)
    full = total_eighths // 8
    partial = total_eighths % 8
    bar = "█" * full + (blocks[8 - partial] if partial else "")
    return bar.ljust(max_blocks)


def _ndvi_chart(ndvi_series: list[float], baseline: float) -> str:
    if not ndvi_series:
        return ""
    recent = ndvi_series[-6:]
    n = len(recent)
    lines = ["📊 *NDVI Trend (your farm):*"]
    for i, v in enumerate(recent):
        weeks_ago = n - i
        is_trigger = i == n - 1 and v < baseline * 0.8
        label = "NOW →  " if i == n - 1 else f"Wk -{weeks_ago}  "
        flag = " ⚠️" if v < baseline * 0.85 and not is_trigger else (" 🔴" if is_trigger else "")
        lines.append(f"  {label}: {_ndvi_bar(v)} {v:.2f}{flag}")
    lines.append(f"  Baseline: {_ndvi_bar(baseline)} {baseline:.2f} ──")
    return "\n".join(lines)


# ── Public notification functions ─────────────────────────────────────────────

async def send_enrollment_confirmation(
    phone: str,
    farmer_name: str,
    policy_id: str,
    farm_id: str,
) -> None:
    """Welcome message sent immediately after enrollment."""
    short = policy_id[:8].upper()

    sms = (
        f"Karibu CropSure, {farmer_name}! Bima: {short}. "
        "Shamba lako linaangaliwa kutoka angani kila siku 5. "
        f"Welcome to CropSure! Policy: {short}. "
        "Your farm is monitored from space every 5 days."
    )

    wa = (
        f"🌱 *Karibu CropSure AI, {farmer_name}!*\n\n"
        f"Shamba lako sasa lina bima. / Your farm is now insured.\n\n"
        f"📋 *Nambari ya Bima / Policy:* `{short}`\n\n"
        "Tutafuatilia shamba lako kwa setilaiti kila siku 5.\n"
        "We will monitor your farm by satellite every 5 days.\n\n"
        "*Amri za WhatsApp / WhatsApp Commands:*\n"
        "• *shamba* — Hali ya shamba lako / Your farm health\n"
        "• *ushauri* — Ushauri wa kilimo / Farming advice\n"
        "• *ndvi* — Mwelekeo wa NDVI / NDVI trend\n"
        "• *malipo* — Historia ya malipo / Payout history\n"
        "• *help* — Orodha ya amri / Command list\n\n"
        "Ukipata tatizo lolote, tutakujulisha moja kwa moja. 🛰️\n"
        "If any issue is detected, we will notify you directly."
    )

    for fn, arg in [(send_sms, sms), (send_whatsapp, wa)]:
        try:
            await fn(phone, arg)
        except Exception as e:
            logger.error("%s failed for %s: %s", fn.__name__, phone, e)


async def send_farm_progress_update(
    phone: str,
    farmer_name: str,
    crop_type: str,
    ndvi_current: float,
    ndvi_baseline: float,
    deviation_pct: float,
    stress_type: str,
    ndvi_series: Optional[list[float]] = None,
) -> None:
    """
    Proactive update sent after every satellite pass.
    Healthy farms get a brief positive confirmation.
    Mild-stress farms get an early warning with advice.
    """
    dev_str = f"{deviation_pct:+.1f}%"
    is_ok = stress_type in ("no_stress", "healthy") or stress_type is None

    if is_ok:
        icon = "✅"
        status_en = f"Your {crop_type} farm is healthy this week."
        status_sw = f"Shamba lako la {crop_type} ni zuri wiki hii."
    else:
        icon = "⚠️"
        status_en = f"Early warning: {crop_type} showing mild stress signs."
        status_sw = f"Onyo la awali: {crop_type} inaonyesha dalili za msongo mdogo."

    sms = (
        f"CropSure: {status_en} "
        f"NDVI {ndvi_current:.2f} ({dev_str} vs baseline). "
        f"CropSure: {status_sw} "
        f"NDVI {ndvi_current:.2f} ({dev_str} dhidi ya kawaida)."
    )

    chart = _ndvi_chart(ndvi_series or [ndvi_current], ndvi_baseline) if ndvi_series else ""

    advice_en = _advice(stress_type if not is_ok else "healthy", "en")
    advice_sw = _advice(stress_type if not is_ok else "healthy", "sw")

    wa = (
        f"{icon} *CropSure — Ripoti ya Wiki / Weekly Farm Report*\n\n"
        f"Habari {farmer_name},\n\n"
        f"🌿 *Hali / Status:* {status_sw}\n"
        f"   {status_en}\n\n"
        f"📈 *NDVI:* {ndvi_current:.3f}  ({dev_str} vs baseline {ndvi_baseline:.3f})\n"
    )
    if chart:
        wa += f"\n{chart}\n"
    wa += (
        f"\n{advice_sw}\n\n"
        f"{advice_en}\n\n"
        "🛰️ Setilaiti itafanya uchambuzi mwingine baada ya siku 5.\n"
        "Next satellite analysis in 5 days."
    )

    for fn, msg in [(send_sms, sms), (send_whatsapp, wa)]:
        try:
            await fn(phone, msg)
        except Exception as e:
            logger.error("%s progress update failed for %s: %s", fn.__name__, phone, e)


async def send_early_warning(
    phone: str,
    farmer_name: str,
    crop_type: str,
    ndvi_current: float,
    ndvi_baseline: float,
    deviation_pct: float,
    stress_type: str,
    ndvi_series: Optional[list[float]] = None,
) -> None:
    """
    Urgent early warning — NDVI dropping fast but payout not yet triggered.
    Sent when confidence is below threshold but stress is visible.
    """
    dev_str = f"{deviation_pct:.1f}%"

    sms = (
        f"CropSure ONYO / WARNING: {farmer_name}, NDVI yako imeshuka {dev_str} "
        f"chini ya kawaida. Chukua hatua sasa! / Your NDVI dropped {dev_str} "
        "below baseline. Take action now!"
    )

    chart = _ndvi_chart(ndvi_series or [ndvi_current], ndvi_baseline) if ndvi_series else ""
    advice_en = _advice(stress_type, "en")
    advice_sw = _advice(stress_type, "sw")

    wa = (
        f"🚨 *CropSure — Onyo la Mapema / Early Warning*\n\n"
        f"Habari {farmer_name},\n\n"
        f"Setilaiti imeona mwelekeo wa kushuka kwa mazao yako ya *{crop_type}*.\n"
        f"Satellite detected a declining trend on your *{crop_type}* farm.\n\n"
        f"📉 *NDVI ya sasa / Current NDVI:* {ndvi_current:.3f}\n"
        f"📊 *Kawaida / Baseline:* {ndvi_baseline:.3f}\n"
        f"⬇️ *Kushuka / Drop:* {dev_str} below your personal baseline\n"
    )
    if chart:
        wa += f"\n{chart}\n"
    wa += (
        f"\n{advice_sw}\n\n"
        f"{advice_en}\n\n"
        "⚠️ Ikiwa hali itaendelea kushuka, malipo yatatumwa kiotomatiki.\n"
        "If conditions continue to decline, a payout will be sent automatically.\n\n"
        "Jibu *ushauri* kwa zaidi. / Reply *advice* for more."
    )

    for fn, msg in [(send_sms, sms), (send_whatsapp, wa)]:
        try:
            await fn(phone, msg)
        except Exception as e:
            logger.error("%s early warning failed for %s: %s", fn.__name__, phone, e)


async def send_payout_notification(
    phone: str,
    farmer_name: str,
    amount_kes: float,
    explanation_en: str,
    explanation_sw: str,
    ndvi_series: Optional[list[float]] = None,
    baseline_ndvi: Optional[float] = None,
    stress_type: str = "drought",
) -> None:
    """Full payout alert — M-Pesa sent, includes NDVI chart and recovery advice."""
    amount_fmt = f"KES {int(amount_kes):,}"

    sms = (
        f"CropSure: {explanation_en} "
        f"{amount_fmt} imetumwa M-Pesa yako. / {amount_fmt} sent to your M-Pesa. "
        f"{explanation_sw}"
    )

    chart = ""
    if ndvi_series and baseline_ndvi:
        chart = "\n\n" + _ndvi_chart(ndvi_series, baseline_ndvi)

    advice_en = _advice(stress_type, "en")
    advice_sw = _advice(stress_type, "sw")

    wa = (
        f"💸 *CropSure — Malipo Yametumwa / Payout Sent*\n\n"
        f"Habari {farmer_name},\n\n"
        f"*{amount_fmt}* imetumwa kwa M-Pesa yako.\n"
        f"*{amount_fmt}* has been sent to your M-Pesa.\n\n"
        f"📋 *Sababu / Reason (SW):* {explanation_sw}\n"
        f"📋 *Reason (EN):* {explanation_en}"
        f"{chart}\n\n"
        f"{advice_sw}\n\n"
        f"{advice_en}\n\n"
        "Jibu *shamba* kuona hali ya sasa. / Reply *shamba* to see current status.\n"
        "🛰️ Ufuatiliaji unaendelea. / Monitoring continues."
    )

    for fn, msg in [(send_sms, sms), (send_whatsapp, wa)]:
        try:
            await fn(phone, msg)
        except Exception as e:
            logger.error("%s payout notification failed for %s: %s", fn.__name__, phone, e)
