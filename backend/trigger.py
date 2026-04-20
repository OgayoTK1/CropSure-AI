"""
Monitoring cycle pipeline — fetch farm indicators, detect drought, notify, payout.

Drought thresholds (configurable via env):
  NDVI_DROUGHT_THRESHOLD   — NDVI below this value signals crop stress   (default 0.35)
  RAINFALL_DROUGHT_MM      — Rainfall below this (mm/month) triggers payout (default 50.0)

Weather data source: OpenWeatherMap current weather API (free tier).
NDVI is simulated here; swap _fetch_ndvi() with a real satellite API (e.g. Sentinel Hub).
"""
import os
import logging
import random
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Farm, Farmer, MonitoringCycle, MpesaTransaction
from mpesa import b2c_payment
from notifications import notify_farmer

logger = logging.getLogger(__name__)

OWM_API_KEY = os.getenv("OWM_API_KEY", "")
NDVI_DROUGHT_THRESHOLD = float(os.getenv("NDVI_DROUGHT_THRESHOLD", "0.35"))
RAINFALL_DROUGHT_MM = float(os.getenv("RAINFALL_DROUGHT_MM", "50.0"))


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------

async def _fetch_rainfall(lat: float, lon: float) -> float:
    """
    Fetch current rainfall (mm) from OpenWeatherMap for the given coordinates.
    Returns 0.0 if the API key is unset or the request fails.
    """
    if not OWM_API_KEY:
        logger.warning("OWM_API_KEY not set — rainfall defaulting to 0.0")
        return 0.0

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    rain = data.get("rain", {})
    return float(rain.get("1h", rain.get("3h", 0.0)))


def _fetch_ndvi(lat: float, lon: float) -> float:
    """
    Return a simulated NDVI score (0–1).
    Replace with a real satellite imagery API call (Sentinel Hub, Planet, etc.).
    """
    # Seeded by coordinates so the same farm gets consistent results in tests.
    rng = random.Random(f"{lat:.4f}{lon:.4f}{datetime.utcnow().strftime('%Y%m%d')}")
    return round(rng.uniform(0.20, 0.70), 4)


# ---------------------------------------------------------------------------
# Drought detection
# ---------------------------------------------------------------------------

def is_drought(ndvi: float, rainfall_mm: float) -> bool:
    return ndvi < NDVI_DROUGHT_THRESHOLD or rainfall_mm < RAINFALL_DROUGHT_MM


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

async def _process_farm(farm: Farm, farmer: Farmer, db: AsyncSession) -> MonitoringCycle:
    """Run one monitoring cycle for a single farm."""
    rainfall = await _fetch_rainfall(farm.latitude, farm.longitude)
    ndvi = _fetch_ndvi(farm.latitude, farm.longitude)
    drought = is_drought(ndvi, rainfall)

    cycle = MonitoringCycle(
        farm_id=farm.id,
        ndvi_score=ndvi,
        rainfall_mm=rainfall,
        drought_detected=drought,
    )
    db.add(cycle)
    await db.flush()  # get cycle.id without committing

    if drought:
        message = (
            f"Dear {farmer.full_name}, drought conditions detected on your farm "
            f"'{farm.name}' (NDVI={ndvi}, Rainfall={rainfall}mm). "
            f"A payout of KES {farm.payout_amount:,.0f} is being processed."
        )
        try:
            await notify_farmer(farmer.phone_number, message)
            cycle.alert_sent = True
        except Exception as exc:
            logger.error("Notification failed for farm %s: %s", farm.id, exc)

        try:
            result = await b2c_payment(
                phone=farmer.phone_number,
                amount=int(farm.payout_amount),
                remarks=f"Drought payout - {farm.name}",
            )
            tx = MpesaTransaction(
                transaction_type="B2C",
                conversation_id=result.get("ConversationID"),
                phone_number=farmer.phone_number,
                amount=farm.payout_amount,
                status="pending",
                farm_id=farm.id,
            )
            db.add(tx)
            cycle.payout_initiated = True
        except Exception as exc:
            logger.error("B2C payout failed for farm %s: %s", farm.id, exc)

    cycle.notes = f"NDVI={ndvi}, Rainfall={rainfall}mm, Drought={drought}"
    return cycle


async def run_monitoring_cycle(db: AsyncSession) -> list[dict]:
    """
    Run the full monitoring cycle for all active farms.
    Returns a summary list of cycle results.
    """
    result = await db.execute(
        select(Farm, Farmer)
        .join(Farmer, Farm.farmer_id == Farmer.id)
        .where(Farm.is_active.is_(True))
    )
    rows = result.all()

    summaries = []
    for farm, farmer in rows:
        try:
            cycle = await _process_farm(farm, farmer, db)
            summaries.append({
                "farm_id": str(farm.id),
                "farm_name": farm.name,
                "ndvi": cycle.ndvi_score,
                "rainfall_mm": cycle.rainfall_mm,
                "drought_detected": cycle.drought_detected,
                "alert_sent": cycle.alert_sent,
                "payout_initiated": cycle.payout_initiated,
            })
        except Exception as exc:
            logger.error("Monitoring failed for farm %s: %s", farm.id, exc)
            summaries.append({"farm_id": str(farm.id), "error": str(exc)})

    return summaries


async def simulate_drought(farm_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    Force-inject a drought cycle for a specific farm (for testing/demos).
    Bypasses real weather data and uses threshold-breaking values.
    """
    result = await db.execute(
        select(Farm, Farmer)
        .join(Farmer, Farm.farmer_id == Farmer.id)
        .where(Farm.id == farm_id)
    )
    row = result.first()
    if not row:
        raise ValueError(f"Farm {farm_id} not found")

    farm, farmer = row
    ndvi = NDVI_DROUGHT_THRESHOLD - 0.05          # just below threshold
    rainfall = RAINFALL_DROUGHT_MM - 10.0         # just below threshold

    cycle = MonitoringCycle(
        farm_id=farm.id,
        ndvi_score=ndvi,
        rainfall_mm=rainfall,
        drought_detected=True,
        notes="Simulated drought cycle",
    )
    db.add(cycle)
    await db.flush()

    message = (
        f"[SIMULATION] Dear {farmer.full_name}, drought conditions detected on "
        f"'{farm.name}'. Payout of KES {farm.payout_amount:,.0f} would be triggered."
    )
    try:
        await notify_farmer(farmer.phone_number, message)
        cycle.alert_sent = True
    except Exception as exc:
        logger.error("Simulation notification failed: %s", exc)

    return {
        "farm_id": str(farm.id),
        "farm_name": farm.name,
        "ndvi": ndvi,
        "rainfall_mm": rainfall,
        "drought_detected": True,
        "alert_sent": cycle.alert_sent,
        "payout_initiated": False,
        "note": "Simulation — no real B2C payout triggered",
    }
