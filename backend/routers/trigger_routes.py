"""
Monitoring cycle trigger endpoints.

POST /trigger/run                       — run full monitoring cycle for all active farms
POST /trigger/simulate-drought/{farm_id} — force a drought cycle on one farm (no real B2C)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from trigger import run_monitoring_cycle, simulate_drought

router = APIRouter()


@router.post("/run")
async def run_trigger(db: AsyncSession = Depends(get_db)):
    """
    Runs the monitoring pipeline for every active farm:
    1. Fetch NDVI + rainfall data
    2. Detect drought conditions
    3. Send SMS/WhatsApp alerts
    4. Initiate M-Pesa B2C payouts where triggered
    """
    summaries = await run_monitoring_cycle(db)
    drought_count = sum(1 for s in summaries if s.get("drought_detected"))
    return {
        "farms_checked": len(summaries),
        "droughts_detected": drought_count,
        "results": summaries,
    }


@router.post("/simulate-drought/{farm_id}")
async def simulate_drought_route(farm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Inject a simulated drought event for a single farm.
    Sends a notification but does NOT trigger a real M-Pesa B2C payout.
    Useful for demos and integration testing.
    """
    try:
        result = await simulate_drought(farm_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result
