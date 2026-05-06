"""Monitoring cycle and payout trigger pipeline."""

import logging
from datetime import datetime, timedelta, date

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Farm, Policy, PolicyStatus, NDVIReading, Payout, PayoutStatus, Baseline
from .mpesa import b2c_payment
from .notifications import send_payout_notification
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

PAYOUT_COOLDOWN_DAYS = 30


async def _call_ml_analyze(farm: Farm, baseline_data: dict, session: AsyncSession) -> dict:
    """Call the ML microservice /analyze endpoint."""
    recent = (
        await session.execute(
            select(NDVIReading)
            .where(NDVIReading.farm_id == farm.id)
            .order_by(NDVIReading.reading_date.desc())
            .limit(3)
        )
    ).scalars().all()
    recent_series = [r.ndvi_value for r in reversed(recent)]

    payload = {
        "farm_id": farm.id,
        "polygon_geojson": farm.polygon_geojson,
        "baseline_dict": baseline_data,
        "recent_ndvi_series": recent_series,
    }
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{settings.ml_service_url}/analyze", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()


async def _has_recent_payout(farm_id: str, session: AsyncSession) -> bool:
    cutoff = datetime.utcnow() - timedelta(days=PAYOUT_COOLDOWN_DAYS)
    result = await session.execute(
        select(Payout)
        .where(Payout.farm_id == farm_id, Payout.triggered_at >= cutoff, Payout.status != PayoutStatus.failed)
    )
    return result.scalars().first() is not None


async def _get_active_policy(farm_id: str, session: AsyncSession):
    result = await session.execute(
        select(Policy).where(Policy.farm_id == farm_id, Policy.status == PolicyStatus.active)
    )
    return result.scalars().first()


async def process_farm(farm: Farm, session: AsyncSession) -> dict:
    """Run full monitoring + trigger pipeline for one farm. Returns analysis result."""
    baseline_row = (await session.execute(
        select(Baseline).where(Baseline.farm_id == farm.id)
    )).scalars().first()

    if not baseline_row:
        logger.warning("No baseline for farm %s — skipping", farm.id)
        return {"farm_id": farm.id, "skipped": True, "reason": "no_baseline"}

    analysis = await _call_ml_analyze(farm, baseline_row.baseline_data, session)

    # Persist NDVI reading
    reading = NDVIReading(
        farm_id=farm.id,
        reading_date=date.today(),
        ndvi_value=analysis.get("ndvi_current", 0.0),
        ndvi_zscore=analysis.get("ndvi_zscore"),
        stress_type=analysis.get("stress_type"),
        confidence=analysis.get("confidence"),
        cloud_contaminated=analysis.get("cloud_contaminated", False),
    )
    session.add(reading)

    if analysis.get("payout_recommended"):
        await _maybe_trigger_payout(farm, analysis, session)

    await session.commit()
    return analysis


async def _maybe_trigger_payout(farm: Farm, analysis: dict, session: AsyncSession) -> None:
    policy = await _get_active_policy(farm.id, session)
    if not policy:
        logger.info("No active policy for farm %s — payout skipped", farm.id)
        return

    if await _has_recent_payout(farm.id, session):
        logger.info("Farm %s already paid out recently — skipping", farm.id)
        return

    payout_amount = min(policy.coverage_amount_kes * 0.4, policy.coverage_amount_kes)

    payout = Payout(
        policy_id=policy.id,
        farm_id=farm.id,
        payout_amount_kes=payout_amount,
        stress_type=analysis["stress_type"],
        explanation_en=analysis.get("explanation_en", ""),
        explanation_sw=analysis.get("explanation_sw", ""),
        status=PayoutStatus.processing,
    )
    session.add(payout)
    await session.flush()  # get payout.id

    try:
        result = await b2c_payment(
            phone=farm.phone_number,
            amount=payout_amount,
            remarks=f"CropSure payout — {analysis['stress_type']}",
        )
        payout.mpesa_conversation_id = result.get("ConversationID")
        if result.get("ResponseCode") == "0":
            payout.status = PayoutStatus.completed
            payout.completed_at = datetime.utcnow()
        else:
            payout.status = PayoutStatus.failed
    except Exception as e:
        logger.error("B2C payment failed for farm %s: %s", farm.id, e)
        payout.status = PayoutStatus.failed

    if payout.status == PayoutStatus.completed:
        await send_payout_notification(
            phone=farm.phone_number,
            farmer_name=farm.farmer_name,
            amount_kes=payout_amount,
            explanation_en=analysis.get("explanation_en", ""),
            explanation_sw=analysis.get("explanation_sw", ""),
        )


async def run_monitoring_cycle(session: AsyncSession) -> dict:
    """Fetch all active farms and run the monitoring pipeline for each."""
    result = await session.execute(
        select(Farm).join(Policy).where(Policy.status == PolicyStatus.active)
    )
    farms = result.scalars().unique().all()
    logger.info("Monitoring cycle started — %d active farms", len(farms))

    outcomes = []
    for farm in farms:
        try:
            outcome = await process_farm(farm, session)
            outcomes.append(outcome)
        except Exception as e:
            logger.error("Error processing farm %s: %s", farm.id, e)
            outcomes.append({"farm_id": farm.id, "error": str(e)})

    return {"farms_processed": len(farms), "outcomes": outcomes}
