"""
CropSure AI USSD handler — Africa's Talking *384#

State machine driven entirely by the accumulating `text` field that
Africa's Talking sends with each menu selection joined by '*'.

Menu structure
--------------
0 (entry)       Main menu: 1=Enroll  2=Check Status  3=Payout History
1*<name>        Enroll step 2: ask village
1*n*<village>   Enroll step 3: crop type menu
1*n*v*<crop>    Enroll step 4: ask farm size in acres
1*n*v*c*<acres> Enroll step 5: show premium, ask confirm (1=Pay / 2=Cancel)
1*n*v*c*a*1     Confirm → call backend API, END with policy confirmation
1*n*v*c*a*2     Cancel → END
2*<phone>       Status check → call backend API
3*<phone>       Payout history → call backend API
"""

import os
import math
import logging
from typing import Optional

import httpx
from fastapi import FastAPI, Form, Response
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CropSure USSD Handler")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
PREMIUM_PER_ACRE = int(os.getenv("PREMIUM_PER_ACRE", "300"))
COVERAGE_MULTIPLIER = int(os.getenv("COVERAGE_MULTIPLIER", "8"))

CROPS = ["Maize", "Beans", "Tea", "Wheat", "Sorghum", "Coffee", "Cassava"]

# ── GeoJSON helpers ──────────────────────────────────────────────────────────

def _acres_to_m2(acres: float) -> float:
    return acres * 4047.0


def _default_polygon(acres: float) -> dict:
    """
    Build a rough square polygon around Nairobi whose area approximates the given acreage.
    Used when GPS walk is not available (USSD path).
    Side length in degrees ≈ sqrt(area_m2) / 111_320
    """
    side_m = math.sqrt(_acres_to_m2(acres))
    delta = side_m / 111_320 / 2
    lat, lng = -1.2921, 36.8219  # Nairobi centre — will be updated from village lookup
    coords = [
        [lng - delta, lat - delta],
        [lng + delta, lat - delta],
        [lng + delta, lat + delta],
        [lng - delta, lat + delta],
        [lng - delta, lat - delta],
    ]
    return {"type": "Polygon", "coordinates": [coords]}


# ── Session helpers ──────────────────────────────────────────────────────────

def _parts(text: str) -> list[str]:
    """Split accumulated AT text into individual inputs."""
    return [p.strip() for p in text.split("*")] if text else []


def _crop_menu() -> str:
    return "\n".join(f"{i + 1}. {c}" for i, c in enumerate(CROPS))


# ── Backend calls ────────────────────────────────────────────────────────────

async def _enroll(phone: str, name: str, village: str, crop: str, acres: float) -> Optional[dict]:
    try:
        polygon = _default_polygon(acres)
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                f"{BACKEND_URL}/farms/enroll",
                json={
                    "farmer_name": name,
                    "phone_number": phone,
                    "village": village,
                    "crop_type": crop,
                    "polygon_geojson": polygon,
                },
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.error("USSD enroll failed: %s", e)
        return None


async def _get_status(phone: str) -> Optional[dict]:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{BACKEND_URL}/farms", params={"phone": phone})
            r.raise_for_status()
            farms = r.json()
            return farms[0] if farms else None
    except Exception as e:
        logger.error("USSD status check failed: %s", e)
        return None


# ── Main USSD endpoint ───────────────────────────────────────────────────────

@app.post("/ussd")
async def ussd(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(""),
) -> Response:
    """Africa's Talking USSD webhook. Returns CON/END plain text."""

    parts = _parts(text)
    level = len(parts)
    resp = _handle(parts, level, phoneNumber)
    return Response(content=resp, media_type="text/plain")


def _handle(parts: list[str], level: int, phone: str) -> str:
    # ── Entry: show main menu ────────────────────────────────────────────────
    if level == 0 or (level == 1 and parts[0] == ""):
        return (
            "CON Karibu CropSure AI / Welcome to CropSure AI\n"
            "1. Jiandikishe / Enroll Farm\n"
            "2. Hali ya Bima / Check Policy\n"
            "3. Historia ya Malipo / Payout History"
        )

    choice = parts[0]

    # ── Branch 1: Enroll ─────────────────────────────────────────────────────
    if choice == "1":
        if level == 1:
            return "CON Jina lako kamili / Your full name:"

        if level == 2:
            return "CON Kijiji au eneo / Village or location:"

        if level == 3:
            return f"CON Aina ya zao / Crop type:\n{_crop_menu()}"

        if level == 4:
            crop_idx = int(parts[3]) - 1
            if not (0 <= crop_idx < len(CROPS)):
                return "END Chaguo si sahihi. / Invalid choice."
            return "CON Ukubwa wa shamba (ekari) / Farm size (acres, e.g. 2.5):"

        if level == 5:
            try:
                acres = float(parts[4])
                if acres <= 0 or acres > 1000:
                    raise ValueError("out of range")
            except ValueError:
                return "END Ukubwa si sahihi. / Invalid farm size."
            crop_idx = int(parts[3]) - 1
            premium = max(1, round(acres * PREMIUM_PER_ACRE))
            coverage = premium * COVERAGE_MULTIPLIER
            crop = CROPS[crop_idx]
            return (
                f"CON {crop} | {acres} ekari\n"
                f"Ada ya bima: KES {premium:,}\n"
                f"Fidia: KES {coverage:,}\n"
                f"Premium: KES {premium:,} / Coverage: KES {coverage:,}\n"
                "1. Thibitisha na Lipa / Confirm & Pay\n"
                "2. Ghairi / Cancel"
            )

        if level == 6:
            confirm = parts[5]
            if confirm == "2":
                return "END Umeghairi. Asante. / Cancelled. Thank you."
            if confirm != "1":
                return "END Chaguo si sahihi. / Invalid choice."

            # All inputs collected — perform enrollment via backend
            name = parts[1]
            village = parts[2]
            crop_idx = int(parts[3]) - 1
            crop = CROPS[crop_idx]
            try:
                acres = float(parts[4])
            except ValueError:
                return "END Hitilafu ya data. / Data error."

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                _enroll(phone, name, village, crop, acres)
            )

            if not result:
                return (
                    "END Hitilafu ya mtandao. Jaribu tena baadaye.\n"
                    "Network error. Please try again later."
                )

            policy_id = result.get("policy_id", "")[:8].upper()
            premium = result.get("premium_amount_kes", round(acres * PREMIUM_PER_ACRE))
            return (
                f"END Shamba limeandikishwa! / Farm Enrolled!\n"
                f"Bima: {policy_id}\n"
                f"Ombi la M-Pesa la KES {premium:,} limetumwa.\n"
                f"M-Pesa prompt of KES {premium:,} sent.\n"
                "Shamba lako linaangaliwa kutoka angani.\n"
                "Your farm is now monitored from space."
            )

        return "END Hitilafu. / Error."

    # ── Branch 2: Check Policy Status ────────────────────────────────────────
    if choice == "2":
        if level == 1:
            return "CON Nambari ya M-Pesa yako / Your M-Pesa number (07XXXXXXXX):"

        if level == 2:
            import asyncio
            farm = asyncio.get_event_loop().run_until_complete(_get_status(parts[1]))
            if not farm:
                return (
                    "END Hakuna bima iliyopatikana kwa nambari hiyo.\n"
                    "No policy found for that number."
                )
            health = farm.get("health_status", "unknown")
            status = farm.get("policy_status", "unknown")
            name = farm.get("farmer_name", "")
            return (
                f"END Habari, {name}!\n"
                f"Hali ya bima: {status}\n"
                f"Afya ya shamba: {health}\n"
                f"Policy: {status} | Farm health: {health}\n"
                "Angalia app kwa maelezo zaidi.\n"
                "Check the app for more details."
            )

        return "END Hitilafu. / Error."

    # ── Branch 3: Payout History ──────────────────────────────────────────────
    if choice == "3":
        if level == 1:
            return "CON Nambari ya M-Pesa yako / Your M-Pesa number (07XXXXXXXX):"

        if level == 2:
            import asyncio
            farm = asyncio.get_event_loop().run_until_complete(_get_status(parts[1]))
            if not farm:
                return (
                    "END Hakuna rekodi iliyopatikana.\n"
                    "No records found for that number."
                )
            payouts = farm.get("payouts", [])
            if not payouts:
                return (
                    "END Hakuna malipo bado. Shamba lako ni zuri!\n"
                    "No payouts yet. Your farm is healthy!"
                )
            lines = []
            for p in payouts[:3]:
                amt = p.get("amount_kes", 0)
                st = p.get("stress_type", "")
                dt = p.get("triggered_at", "")[:10]
                lines.append(f"KES {amt:,} — {st} ({dt})")
            history = "\n".join(lines)
            return f"END Historia ya Malipo / Payout History:\n{history}"

        return "END Hitilafu. / Error."

    return "END Chaguo si sahihi. / Invalid option."


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "ussd-handler"}
