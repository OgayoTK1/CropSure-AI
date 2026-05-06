"""
Monitoring cycle pipeline.

Flow per active policy:
  1. Call ML /analyze with farm polygon → NDVI + stress assessment
  2. Store NdviReading
  3. If payout_recommended AND no payout in last 30 days:
       a. Create Payout record (status=processing)
       b. Initiate M-Pesa B2C
       c. Store ConversationID on payout
       d. Send SMS + WhatsApp bilingual alert
"""
import logging
import os
import uuid
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Farm, Policy, NdviReading, Payout, PolicyStatus, PayoutStatus
from mpesa import b2c_payment
from notifications import send_payout_notification

logger = logging.getLogger(__name__)

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")


# ---------------------------------------------------------------------------
# ML service helpers
# ---------------------------------------------------------------------------

async def _call_ml_analyze(farm_id: str, polygon_geojson: dict) -> dict:
    """
    POST {ML_SERVICE_URL}/analyze
    Expected response:
      { ndvi_value, stress_type, confidence, cloud_contaminated,
        payout_recommended, payout_amount_kes, explanation_en, explanation_sw }
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{ML_SERVICE_URL}/analyze",
            json={"farm_id": farm_id, "polygon_geojson": polygon_geojson},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def call_ml_baseline(farm_id: str, polygon_geojson: dict) -> None:
    """Fire-and-forget: build NDVI baseline for a newly enrolled farm."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{ML_SERVICE_URL}/build-baseline",
                json={"farm_id": farm_id, "polygon_geojson": polygon_geojson},
                timeout=60,
            )
        logger.info("ML baseline build requested for farm %s", farm_id)
    except Exception as exc:
        logger.error("ML baseline build failed for farm %s: %s", farm_id, exc)


# ---------------------------------------------------------------------------
# Payout guard
# ---------------------------------------------------------------------------

async def _has_recent_payout(farm_id: uuid.UUID, db: AsyncSession) -> bool:
    """Return True if a non-failed payout was triggered in the last 30 days."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(Payout).where(
            Payout.farm_id == farm_id,
            Payout.triggered_at >= cutoff,
            Payout.status.notin_([PayoutStatus.failed]),
        )
    )
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

async def _process_policy(policy: Policy, farm: Farm, db: AsyncSession) -> dict:
    """Run one monitoring cycle for a single active policy."""
    ml = await _call_ml_analyze(str(farm.id), farm.polygon_geojson)

    reading = NdviReading(
        farm_id=farm.id,
        reading_date=datetime.utcnow().date(),
        ndvi_value=ml["ndvi_value"],
        stress_type=ml.get("stress_type"),
        confidence=ml.get("confidence"),
        cloud_contaminated=ml.get("cloud_contaminated", False),
    )
    db.add(reading)
    await db.flush()

    summary = {
        "farm_id": str(farm.id),
        "farm_name": farm.village,
        "ndvi_value": ml["ndvi_value"],
        "stress_type": ml.get("stress_type"),
        "payout_triggered": False,
    }

    if not ml.get("payout_recommended"):
        return summary

    if await _has_recent_payout(farm.id, db):
        summary["skipped"] = "payout already issued in last 30 days"
        return summary

    # Create payout record
    payout = Payout(
        policy_id=policy.id,
        farm_id=farm.id,
        payout_amount_kes=ml["payout_amount_kes"],
        stress_type=ml.get("stress_type", "unknown"),
        explanation_en=ml.get("explanation_en", ""),
        explanation_sw=ml.get("explanation_sw", ""),
        status=PayoutStatus.processing,
    )
    db.add(payout)
    await db.flush()

    # Initiate B2C
    try:
        b2c_resp = await b2c_payment(
            phone=farm.phone_number,
            amount=int(ml["payout_amount_kes"]),
            remarks=f"CropSure payout - {farm.village} ({ml.get('stress_type', '')})",
        )
        payout.mpesa_transaction_id = b2c_resp.get("ConversationID")
        summary["payout_triggered"] = True
        summary["conversation_id"] = payout.mpesa_transaction_id
    except Exception as exc:
        logger.error("B2C payout failed for farm %s: %s", farm.id, exc)
        payout.status = PayoutStatus.failed

    # Notify farmer (non-blocking)
    try:
        await send_payout_notification(
            phone=farm.phone_number,
            farmer_name=farm.farmer_name,
            payout_amount_kes=ml["payout_amount_kes"],
            explanation_en=ml.get("explanation_en", ""),
            explanation_sw=ml.get("explanation_sw", ""),
        )
    except Exception as exc:
        logger.error("Notification failed for farm %s: %s", farm.id, exc)

    return summary


async def run_monitoring_cycle(db: AsyncSession) -> list[dict]:
    """
    Run the full monitoring cycle for every active policy.
    Returns a per-farm summary list.
    """
    result = await db.execute(
        select(Policy)
        .options(selectinload(Policy.farm))
        .where(Policy.status == PolicyStatus.active)
    )
    policies = result.scalars().all()

    summaries = []
    for policy in policies:
        try:
            summary = await _process_policy(policy, policy.farm, db)
            summaries.append(summary)
        except Exception as exc:
            logger.error("Monitoring failed for policy %s: %s", policy.id, exc)
            summaries.append({"policy_id": str(policy.id), "error": str(exc)})

    return summaries


async def simulate_drought(farm_id: uuid.UUID, db: AsyncSession) -> dict:
    """
    Force a drought payout pipeline for a specific farm (demo/testing).
    Fires the full pipeline including real B2C and notifications.
    """
    result = await db.execute(
        select(Farm).where(Farm.id == farm_id)
    )
    farm = result.scalar_one_or_none()
    if not farm:
        raise ValueError(f"Farm {farm_id} not found")

    # Get active policy
    pol_result = await db.execute(
        select(Policy).where(
            Policy.farm_id == farm_id,
            Policy.status == PolicyStatus.active,
        )
    )
    policy = pol_result.scalar_one_or_none()
    if not policy:
        raise ValueError(f"No active policy for farm {farm_id}")

    # Build a synthetic ML response
    simulated_ml = {
        "ndvi_value": 0.18,
        "stress_type": "drought",
        "confidence": 0.95,
        "cloud_contaminated": False,
        "payout_recommended": True,
        "payout_amount_kes": policy.coverage_amount_kes * 0.5,
        "explanation_en": "NDVI dropped 48% below your seasonal baseline indicating severe drought stress.",
        "explanation_sw": "NDVI ilishuka asilimia 48 chini ya kiwango cha msimu, ikionyesha ukame mkali.",
    }

    reading = NdviReading(
        farm_id=farm.id,
        reading_date=datetime.utcnow().date(),
        ndvi_value=simulated_ml["ndvi_value"],
        stress_type="drought",
        confidence=0.95,
        cloud_contaminated=False,
    )
    db.add(reading)

    payout = Payout(
        policy_id=policy.id,
        farm_id=farm.id,
        payout_amount_kes=simulated_ml["payout_amount_kes"],
        stress_type="drought",
        explanation_en=simulated_ml["explanation_en"],
        explanation_sw=simulated_ml["explanation_sw"],
        status=PayoutStatus.processing,
    )
    db.add(payout)
    await db.flush()

    b2c_resp = {}
    try:
        b2c_resp = await b2c_payment(
            phone=farm.phone_number,
            amount=int(simulated_ml["payout_amount_kes"]),
            remarks=f"[DEMO] CropSure drought payout - {farm.village}",
        )
        payout.mpesa_transaction_id = b2c_resp.get("ConversationID")
    except Exception as exc:
        logger.error("Demo B2C failed for farm %s: %s", farm.id, exc)
        payout.status = PayoutStatus.failed

    try:
        await send_payout_notification(
            phone=farm.phone_number,
            farmer_name=farm.farmer_name,
            payout_amount_kes=simulated_ml["payout_amount_kes"],
            explanation_en=simulated_ml["explanation_en"],
            explanation_sw=simulated_ml["explanation_sw"],
        )
    except Exception as exc:
        logger.error("Demo notification failed: %s", exc)

    return {
        "farm_id": str(farm.id),
        "farmer_name": farm.farmer_name,
        "simulated_ndvi": simulated_ml["ndvi_value"],
        "payout_amount_kes": simulated_ml["payout_amount_kes"],
        "conversation_id": b2c_resp.get("ConversationID"),
        "payout_status": payout.status,
        "note": "Simulated drought - full pipeline executed",
    }
