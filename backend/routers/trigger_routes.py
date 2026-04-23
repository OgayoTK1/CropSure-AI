"""
Monitoring cycle trigger endpoints.

POST /trigger/run                        — run full monitoring cycle for all active policies
POST /trigger/simulate-drought/{farm_id} — force drought pipeline on one farm (demo)
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
    Runs the monitoring pipeline for every active policy:
    1. Calls ML /analyze per farm
    2. Stores NdviReading
    3. If payout recommended and no recent payout: B2C + notifications
    """
    summaries = await run_monitoring_cycle(db)
    payout_count = sum(1 for s in summaries if s.get("payout_triggered"))
    return {
        "policies_checked": len(summaries),
        "payouts_triggered": payout_count,
        "results": summaries,
    }


@router.post("/simulate-drought/{farm_id}")
async def simulate_drought_route(farm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Inject a simulated drought event for a particular farm.
    Fires the full payout pipeline (real B2C + real notifications).
    Use this for hackathon demos.
    """
    try:
        result = await simulate_drought(farm_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result
