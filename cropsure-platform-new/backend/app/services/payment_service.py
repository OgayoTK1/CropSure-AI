"""Payment orchestration helpers."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Payout, PayoutStatus
from ..mpesa import b2c_payment
from ..notifications import send_payout_notification

logger = logging.getLogger(__name__)


async def execute_payout(
    policy_id: str,
    farm_id: str,
    phone: str,
    farmer_name: str,
    amount_kes: float,
    stress_type: str,
    explanation_en: str,
    explanation_sw: str,
    db: AsyncSession,
) -> Payout:
    payout = Payout(
        policy_id=policy_id,
        farm_id=farm_id,
        payout_amount_kes=amount_kes,
        stress_type=stress_type,
        explanation_en=explanation_en,
        explanation_sw=explanation_sw,
        status=PayoutStatus.processing,
    )
    db.add(payout)
    await db.flush()

    try:
        result = await b2c_payment(phone=phone, amount=amount_kes, remarks=f"CropSure — {stress_type}")
        payout.mpesa_conversation_id = result.get("ConversationID")
        if result.get("ResponseCode") == "0":
            payout.status = PayoutStatus.completed
            payout.completed_at = datetime.utcnow()
        else:
            payout.status = PayoutStatus.failed
    except Exception as e:
        logger.error("B2C failed for farm %s: %s", farm_id, e)
        payout.status = PayoutStatus.failed

    if payout.status == PayoutStatus.completed:
        await send_payout_notification(
            phone=phone, farmer_name=farmer_name,
            amount_kes=amount_kes,
            explanation_en=explanation_en, explanation_sw=explanation_sw,
        )

    return payout
