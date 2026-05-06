"""Farm enrollment and query endpoints."""

import asyncio
import logging
from datetime import date, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from shapely.geometry import shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Farm, Policy, PolicyStatus, Baseline, NDVIReading, Payout
from ..mpesa import stk_push
from ..notifications import send_enrollment_confirmation
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/farms", tags=["farms"])


class EnrollRequest(BaseModel):
    farmer_name: str
    phone_number: str
    village: str
    crop_type: str
    polygon_geojson: dict

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v):
        clean = v.replace(" ", "").replace("-", "")
        if not (clean.startswith("07") or clean.startswith("01") or clean.startswith("254")):
            raise ValueError("Phone must be a valid Kenyan M-Pesa number (07XXXXXXXX or 2547XXXXXXXX)")
        return clean


def _area_acres(polygon_geojson: dict) -> float:
    try:
        geom = shape(polygon_geojson)
        # shapely area in degrees² — approximate to m² using Kenya's latitude factor
        deg_to_m = 111_320
        area_m2 = abs(geom.area) * deg_to_m ** 2
        return round(area_m2 / 4047, 2)
    except Exception:
        return 1.0


async def _fire_baseline_build(farm_id: str, polygon_geojson: dict) -> None:
    """Fire-and-forget baseline build call to ML service."""
    try:
        async with httpx.AsyncClient() as c:
            await c.post(
                f"{settings.ml_service_url}/build-baseline",
                json={"farm_id": farm_id, "polygon_geojson": polygon_geojson},
                timeout=300,
            )
    except Exception as e:
        logger.error("Baseline build task failed for farm %s: %s", farm_id, e)


@router.post("/enroll")
async def enroll_farm(req: EnrollRequest, db: AsyncSession = Depends(get_db)):
    area = _area_acres(req.polygon_geojson)
    if area < 0.1:
        raise HTTPException(status_code=422, detail="Farm polygon is too small (minimum 0.1 acres)")

    premium = round(area * settings.premium_per_acre_kes)
    coverage = round(premium * settings.coverage_multiplier)

    farm = Farm(
        farmer_name=req.farmer_name,
        phone_number=req.phone_number,
        polygon_geojson=req.polygon_geojson,
        area_acres=area,
        crop_type=req.crop_type,
        village=req.village,
    )
    db.add(farm)
    await db.flush()

    season_start = date.today()
    season_end = season_start + timedelta(days=180)
    policy = Policy(
        farm_id=farm.id,
        season_start=season_start,
        season_end=season_end,
        premium_paid_kes=premium,
        coverage_amount_kes=coverage,
        status=PolicyStatus.pending_payment,
    )
    db.add(policy)
    await db.flush()

    stk_result = await stk_push(
        phone=req.phone_number,
        amount=premium,
        account_ref=farm.id[:8].upper(),
        description=f"CropSure insurance premium — {req.crop_type}",
    )
    policy.mpesa_checkout_id = stk_result.get("CheckoutRequestID")

    # If sandbox/simulated, auto-activate
    if stk_result.get("simulated"):
        policy.status = PolicyStatus.active

    await db.commit()

    # Fire baseline build in background (non-blocking)
    asyncio.create_task(_fire_baseline_build(farm.id, req.polygon_geojson))
    asyncio.create_task(send_enrollment_confirmation(req.phone_number, req.farmer_name, policy.id, farm.id))

    return {
        "farm_id": farm.id,
        "policy_id": policy.id,
        "farmer_name": farm.farmer_name,
        "area_acres": area,
        "premium_amount_kes": premium,
        "coverage_amount_kes": coverage,
        "season_start": str(season_start),
        "season_end": str(season_end),
        "mpesa_stk_initiated": True,
        "policy_status": policy.status.value,
    }


@router.get("")
async def list_farms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Farm))
    farms = result.scalars().all()
    output = []
    for f in farms:
        latest = (await db.execute(
            select(NDVIReading).where(NDVIReading.farm_id == f.id).order_by(NDVIReading.reading_date.desc()).limit(1)
        )).scalars().first()

        policy = (await db.execute(
            select(Policy).where(Policy.farm_id == f.id).order_by(Policy.created_at.desc()).limit(1)
        )).scalars().first()

        health = "healthy"
        if latest:
            if latest.stress_type in ("drought", "flood", "pest_disease") and (latest.confidence or 0) > 0.72:
                health = "stress"
            elif latest.stress_type != "no_stress" and latest.stress_type:
                health = "mild_stress"

        output.append({
            "id": f.id,
            "farmer_name": f.farmer_name,
            "phone_number": f.phone_number,
            "village": f.village,
            "crop_type": f.crop_type,
            "area_acres": f.area_acres,
            "polygon_geojson": f.polygon_geojson,
            "health_status": health,
            "current_ndvi": latest.ndvi_value if latest else None,
            "stress_type": latest.stress_type if latest else None,
            "policy_status": policy.status.value if policy else None,
            "created_at": f.created_at.isoformat(),
        })
    return output


@router.get("/{farm_id}")
async def get_farm(farm_id: str, db: AsyncSession = Depends(get_db)):
    farm = (await db.execute(select(Farm).where(Farm.id == farm_id))).scalars().first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    ndvi_rows = (await db.execute(
        select(NDVIReading).where(NDVIReading.farm_id == farm_id).order_by(NDVIReading.reading_date)
    )).scalars().all()

    policy = (await db.execute(
        select(Policy).where(Policy.farm_id == farm_id).order_by(Policy.created_at.desc()).limit(1)
    )).scalars().first()

    payouts = (await db.execute(
        select(Payout).where(Payout.farm_id == farm_id).order_by(Payout.triggered_at.desc())
    )).scalars().all()

    baseline = (await db.execute(
        select(Baseline).where(Baseline.farm_id == farm_id)
    )).scalars().first()

    return {
        "id": farm.id,
        "farmer_name": farm.farmer_name,
        "phone_number": farm.phone_number,
        "village": farm.village,
        "crop_type": farm.crop_type,
        "area_acres": farm.area_acres,
        "polygon_geojson": farm.polygon_geojson,
        "created_at": farm.created_at.isoformat(),
        "policy": {
            "id": policy.id,
            "status": policy.status.value,
            "premium_paid_kes": policy.premium_paid_kes,
            "coverage_amount_kes": policy.coverage_amount_kes,
            "season_start": str(policy.season_start),
            "season_end": str(policy.season_end),
        } if policy else None,
        "ndvi_history": [
            {
                "date": r.reading_date.isoformat(),
                "ndvi": r.ndvi_value,
                "stress_type": r.stress_type,
                "confidence": r.confidence,
            }
            for r in ndvi_rows
        ],
        "baseline_weeks": len(baseline.baseline_data) if baseline else 0,
        "payouts": [
            {
                "id": p.id,
                "amount_kes": p.payout_amount_kes,
                "stress_type": p.stress_type,
                "status": p.status.value,
                "explanation_en": p.explanation_en,
                "explanation_sw": p.explanation_sw,
                "triggered_at": p.triggered_at.isoformat(),
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
            }
            for p in payouts
        ],
    }
