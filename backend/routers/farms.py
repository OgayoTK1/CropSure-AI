"""
Farm enrollment and retrieval endpoints.

POST /farms/enroll   — register a farmer + farm, trigger premium STK push
GET  /farms          — list all farms (with farmer info)
GET  /farms/{farm_id} — get a single farm
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import Farm, Farmer, MpesaTransaction
from mpesa import stk_push

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FarmerIn(BaseModel):
    full_name: str
    phone_number: str = Field(..., examples=["254712345678"])
    national_id: str
    location: str


class FarmIn(BaseModel):
    name: str
    latitude: float
    longitude: float
    acreage: float = Field(..., gt=0)
    crop_type: str = Field(..., examples=["maize", "beans", "coffee"])
    season: str = Field(..., examples=["2026A"])
    premium_amount: float = Field(..., gt=0, description="KES premium to collect via STK")
    payout_amount: float = Field(..., gt=0, description="KES to pay out on drought trigger")


class EnrollRequest(BaseModel):
    farmer: FarmerIn
    farm: FarmIn


class FarmOut(BaseModel):
    id: uuid.UUID
    name: str
    latitude: float
    longitude: float
    acreage: float
    crop_type: str
    season: str
    premium_amount: float
    payout_amount: float
    is_active: bool
    enrolled_at: datetime
    farmer_name: str
    farmer_phone: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_farm(body: EnrollRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new farmer + farm and trigger an M-Pesa STK push to collect
    the first premium payment.
    """
    # Upsert farmer by phone number
    result = await db.execute(
        select(Farmer).where(Farmer.phone_number == body.farmer.phone_number)
    )
    farmer = result.scalar_one_or_none()
    if not farmer:
        farmer = Farmer(**body.farmer.model_dump())
        db.add(farmer)
        await db.flush()

    farm = Farm(farmer_id=farmer.id, **body.farm.model_dump())
    db.add(farm)
    await db.flush()

    # Initiate premium collection via STK Push
    stk_resp = {}
    try:
        stk_resp = await stk_push(
            phone=farmer.phone_number,
            amount=int(farm.premium_amount),
            account_ref=str(farm.id),
            description=f"CropSure Premium - {farm.name}",
        )
        tx = MpesaTransaction(
            transaction_type="STK",
            checkout_request_id=stk_resp.get("CheckoutRequestID"),
            merchant_request_id=stk_resp.get("MerchantRequestID"),
            phone_number=farmer.phone_number,
            amount=farm.premium_amount,
            status="pending",
            farm_id=farm.id,
        )
        db.add(tx)
    except Exception as exc:
        # Enrollment succeeds even if STK push fails — can retry later from the frontend
        stk_resp = {"error": str(exc)}

    return {
        "farm_id": str(farm.id),
        "farmer_id": str(farmer.id),
        "message": "Farm enrolled successfully.",
        "stk_push": stk_resp,
    }


@router.get("", response_model=list[FarmOut])
async def list_farms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Farm).options(selectinload(Farm.farmer)).order_by(Farm.enrolled_at.desc())
    )
    farms = result.scalars().all()
    return [
        FarmOut(
            **{c.name: getattr(f, c.name) for c in Farm.__table__.columns},
            farmer_name=f.farmer.full_name,
            farmer_phone=f.farmer.phone_number,
        )
        for f in farms
    ]


@router.get("/{farm_id}", response_model=FarmOut)
async def get_farm(farm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Farm).options(selectinload(Farm.farmer)).where(Farm.id == farm_id)
    )
    farm = result.scalar_one_or_none()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return FarmOut(
        **{c.name: getattr(farm, c.name) for c in Farm.__table__.columns},
        farmer_name=farm.farmer.full_name,
        farmer_phone=farm.farmer.phone_number,
    )
