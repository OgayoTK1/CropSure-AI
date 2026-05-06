"""Farm query helpers used by multiple routes."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Farm, Policy, NDVIReading, Payout, PolicyStatus


async def get_farm_with_latest(farm_id: str, db: AsyncSession) -> dict | None:
    farm = (await db.execute(select(Farm).where(Farm.id == farm_id))).scalars().first()
    if not farm:
        return None

    latest_ndvi = (await db.execute(
        select(NDVIReading)
        .where(NDVIReading.farm_id == farm_id)
        .order_by(NDVIReading.reading_date.desc())
        .limit(1)
    )).scalars().first()

    policy = (await db.execute(
        select(Policy)
        .where(Policy.farm_id == farm_id)
        .order_by(Policy.created_at.desc())
        .limit(1)
    )).scalars().first()

    health = "healthy"
    if latest_ndvi:
        if latest_ndvi.stress_type not in (None, "no_stress") and (latest_ndvi.confidence or 0) > 0.72:
            health = "stress"
        elif latest_ndvi.stress_type and latest_ndvi.stress_type != "no_stress":
            health = "mild_stress"

    return {
        "farm": farm,
        "latest_ndvi": latest_ndvi,
        "policy": policy,
        "health_status": health,
    }
