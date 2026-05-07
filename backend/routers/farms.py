"""
Farm enrollment and retrieval.

POST /farms/enroll           — register farmer + farm, STK push for premium
GET  /farms/{farm_id}        — farm details + policy + latest NDVI + payout history
GET  /farms                  — admin list with current health status
"""
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Farm, Policy, NdviReading, Payout, PolicyStatus
from mpesa import stk_push
from trigger import call_ml_baseline

logger = logging.getLogger(__name__)
router = APIRouter()

# KES rates
PREMIUM_RATE_PER_ACRE = 300
COVERAGE_MULTIPLIER = 10   # coverage = premium * 10


# ---------------------------------------------------------------------------
# GeoJSON + area helpers
# ---------------------------------------------------------------------------

def _validate_and_area(polygon_geojson: dict) -> float:
    """Validate GeoJSON polygon and return area in acres."""
    from shapely.geometry import shape
    from pyproj import Geod

    if polygon_geojson.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError("polygon_geojson must be a GeoJSON Polygon or MultiPolygon")
    try:
        poly = shape(polygon_geojson)
    except Exception as exc:
        raise ValueError(f"Invalid GeoJSON geometry: {exc}")
    if not poly.is_valid:
        raise ValueError("Polygon geometry is self-intersecting or otherwise invalid")

    geod = Geod(ellps="WGS84")
    area_m2, _ = geod.geometry_area_perimeter(poly)
    return abs(area_m2) / 4046.86   # m² → acres


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class EnrollRequest(BaseModel):
    farmer_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., examples=["254712345678"])
    polygon_geojson: dict
    crop_type: str = Field(..., examples=["maize", "beans", "coffee"])
    village: str

    @field_validator("phone_number")
    @classmethod
    def phone_must_be_safaricom(cls, v: str) -> str:
        import re
        if not re.fullmatch(r"254[71]\d{8}", v):
            raise ValueError("phone_number must be in format 2547XXXXXXXX or 2541XXXXXXXX")
        return v


class PolicyOut(BaseModel):
    id: uuid.UUID
    season_start: datetime
    season_end: datetime
    premium_paid_kes: float
    coverage_amount_kes: float
    status: str
    mpesa_reference: str | None
    created_at: datetime


class NdviOut(BaseModel):
    reading_date: str
    ndvi_value: float
    stress_type: str | None
    confidence: float | None
    cloud_contaminated: bool


class PayoutOut(BaseModel):
    id: uuid.UUID
    payout_amount_kes: float
    stress_type: str
    explanation_en: str
    explanation_sw: str
    status: str
    triggered_at: datetime
    completed_at: datetime | None


class FarmDetailOut(BaseModel):
    id: uuid.UUID
    farmer_name: str
    phone_number: str
    area_acres: float
    crop_type: str
    village: str
    created_at: datetime
    polygon_geojson: dict
    policy: PolicyOut | None
    latest_ndvi: NdviOut | None
    ndvi_history: list[NdviOut]
    payout_history: list[PayoutOut]


class FarmListItem(BaseModel):
    id: uuid.UUID
    farmer_name: str
    phone_number: str
    area_acres: float
    crop_type: str
    village: str
    polygon_geojson: dict
    health_status: str | None   # latest stress_type from NDVI readings
    policy_id: uuid.UUID | None
    policy_status: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_farm(
    body: EnrollRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new farmer + farm.
    - Validates GeoJSON polygon
    - Calculates area via shapely/pyproj
    - Creates Farm + Policy records
    - Fires STK Push for premium (KES 300/acre)
    - Queues ML baseline build in background
    """
    try:
        area_acres = _validate_and_area(body.polygon_geojson)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    premium = round(area_acres * PREMIUM_RATE_PER_ACRE, 2)
    coverage = round(premium * COVERAGE_MULTIPLIER, 2)
    now = datetime.utcnow()

    farm = Farm(
        farmer_name=body.farmer_name,
        phone_number=body.phone_number,
        polygon_geojson=body.polygon_geojson,
        area_acres=area_acres,
        crop_type=body.crop_type,
        village=body.village,
    )
    db.add(farm)
    await db.flush()

    policy = Policy(
        farm_id=farm.id,
        season_start=now,
        season_end=now + timedelta(days=180),
        premium_paid_kes=premium,
        coverage_amount_kes=coverage,
        status=PolicyStatus.pending_payment,
    )
    db.add(policy)
    await db.flush()

    # Initiate premium collection via STK Push
    stk_resp = {}
    mpesa_stk_initiated = False
    try:
        stk_resp = await stk_push(
            phone=body.phone_number,
            amount=int(premium),
            account_ref=str(policy.id),
            description=f"CropSure Premium - {body.village}",
        )
        policy.mpesa_reference = stk_resp.get("CheckoutRequestID")
        mpesa_stk_initiated = True
    except Exception as exc:
        logger.error("STK push failed for farm %s: %s", farm.id, exc)
        stk_resp = {"error": str(exc)}

    # Commit now so mpesa_reference is in the DB before Safaricom fires the callback
    await db.commit()

    # Fire-and-forget ML baseline build
    background_tasks.add_task(call_ml_baseline, str(farm.id), body.polygon_geojson)

    return {
        "farm_id": str(farm.id),
        "policy_id": str(policy.id),
        "premium_amount": premium,
        "mpesa_stk_initiated": mpesa_stk_initiated,
        "stk_response": stk_resp,
    }


@router.get("/{farm_id}", response_model=FarmDetailOut)
async def get_farm(farm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Farm)
        .options(
            selectinload(Farm.policies),
            selectinload(Farm.ndvi_readings),
            selectinload(Farm.payouts),
        )
        .where(Farm.id == farm_id)
    )
    farm = result.scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    active_policy = next(
        (p for p in sorted(farm.policies, key=lambda p: p.created_at, reverse=True)
         if p.status == PolicyStatus.active),
        farm.policies[0] if farm.policies else None,
    )

    sorted_readings = sorted(farm.ndvi_readings, key=lambda r: r.created_at, reverse=True)
    latest = sorted_readings[0] if sorted_readings else None

    ndvi_history_out = [
        NdviOut(
            reading_date=str(r.reading_date),
            ndvi_value=r.ndvi_value,
            stress_type=r.stress_type,
            confidence=r.confidence,
            cloud_contaminated=r.cloud_contaminated,
        )
        for r in sorted(farm.ndvi_readings, key=lambda r: r.created_at)
    ]

    return FarmDetailOut(
        id=farm.id,
        farmer_name=farm.farmer_name,
        phone_number=farm.phone_number,
        area_acres=farm.area_acres,
        crop_type=farm.crop_type,
        village=farm.village,
        created_at=farm.created_at,
        polygon_geojson=farm.polygon_geojson,
        ndvi_history=ndvi_history_out,
        policy=PolicyOut(
            id=active_policy.id,
            season_start=active_policy.season_start,
            season_end=active_policy.season_end,
            premium_paid_kes=active_policy.premium_paid_kes,
            coverage_amount_kes=active_policy.coverage_amount_kes,
            status=active_policy.status.value,
            mpesa_reference=active_policy.mpesa_reference,
            created_at=active_policy.created_at,
        ) if active_policy else None,
        latest_ndvi=NdviOut(
            reading_date=str(latest.reading_date),
            ndvi_value=latest.ndvi_value,
            stress_type=latest.stress_type,
            confidence=latest.confidence,
            cloud_contaminated=latest.cloud_contaminated,
        ) if latest else None,
        payout_history=[
            PayoutOut(
                id=p.id,
                payout_amount_kes=p.payout_amount_kes,
                stress_type=p.stress_type,
                explanation_en=p.explanation_en,
                explanation_sw=p.explanation_sw or '',
                status=p.status.value,
                triggered_at=p.triggered_at,
                completed_at=p.completed_at,
            )
            for p in sorted(farm.payouts, key=lambda p: p.triggered_at, reverse=True)
        ],
    )


@router.get("", response_model=list[FarmListItem])
async def list_farms(db: AsyncSession = Depends(get_db)):
    """Admin dashboard — all farms with current health status."""
    result = await db.execute(
        select(Farm).options(
            selectinload(Farm.policies),
            selectinload(Farm.ndvi_readings),
        ).order_by(Farm.created_at.desc())
    )
    farms = result.scalars().all()

    items = []
    for farm in farms:
        sorted_readings = sorted(farm.ndvi_readings, key=lambda r: r.created_at, reverse=True)
        latest_ndvi = sorted_readings[0] if sorted_readings else None

        active_policy = next(
            (p for p in farm.policies if p.status == PolicyStatus.active), None
        )

        items.append(FarmListItem(
            id=farm.id,
            farmer_name=farm.farmer_name,
            phone_number=farm.phone_number,
            area_acres=farm.area_acres,
            crop_type=farm.crop_type,
            village=farm.village,
            polygon_geojson=farm.polygon_geojson,
            health_status=latest_ndvi.stress_type if latest_ndvi else None,
            policy_id=active_policy.id if active_policy else None,
            policy_status=active_policy.status.value if active_policy else None,
            created_at=farm.created_at,
        ))

    return items
