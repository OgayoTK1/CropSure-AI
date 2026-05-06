"""Manual trigger and demo simulation endpoints."""

import logging
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Farm, Policy, PolicyStatus, Payout, PayoutStatus, Baseline
from ..trigger import run_monitoring_cycle, _maybe_trigger_payout
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/trigger", tags=["trigger"])


@router.post("/run")
async def trigger_monitoring(db: AsyncSession = Depends(get_db)):
    """Manually run the full monitoring cycle for all active farms."""
    result = await run_monitoring_cycle(db)
    return result


@router.post("/simulate-drought/{farm_id}")
async def simulate_drought(farm_id: str, db: AsyncSession = Depends(get_db)):
    """DEMO: Force a drought event for one farm and fire the full payout pipeline."""
    farm = (await db.execute(select(Farm).where(Farm.id == farm_id))).scalars().first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    # Synthesise a drought analysis result
    drought_analysis = {
        "stress_type": "drought",
        "confidence": 0.91,
        "payout_recommended": True,
        "ndvi_current": 0.28,
        "ndvi_baseline_mean": 0.62,
        "ndvi_deviation_pct": -31.5,
        "ndvi_zscore": -2.4,
        "explanation_en": "Vegetation health dropped 31% below your baseline. Drought stress confirmed.",
        "explanation_sw": "Afya ya mazao ilishuka 31% chini ya wastani wako. Ukame umethibitishwa.",
        "simulated": True,
    }

    await _maybe_trigger_payout(farm, drought_analysis, db)
    await db.commit()

    # Fetch the payout just created
    payout = (await db.execute(
        select(Payout).where(Payout.farm_id == farm_id).order_by(Payout.triggered_at.desc()).limit(1)
    )).scalars().first()

    return {
        "farm_id": farm_id,
        "farmer_name": farm.farmer_name,
        "phone": farm.phone_number,
        "payout_amount_kes": payout.payout_amount_kes if payout else 0,
        "payout_status": payout.status.value if payout else "none",
        "analysis": drought_analysis,
        "triggered_at": datetime.utcnow().isoformat(),
    }
