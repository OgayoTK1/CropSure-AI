"""M-Pesa Daraja webhook endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Policy, PolicyStatus, Payout, PayoutStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mpesa", tags=["mpesa"])


@router.post("/stk-callback")
async def stk_callback(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    logger.info("STK callback: %s", body)

    try:
        result = body["Body"]["stkCallback"]
        checkout_id = result["CheckoutRequestID"]
        result_code = result["ResultCode"]

        policy = (await db.execute(
            select(Policy).where(Policy.mpesa_checkout_id == checkout_id)
        )).scalars().first()

        if policy:
            if result_code == 0:
                policy.status = PolicyStatus.active
                items = {i["Name"]: i.get("Value") for i in result.get("CallbackMetadata", {}).get("Item", [])}
                policy.mpesa_reference = str(items.get("MpesaReceiptNumber", ""))
                logger.info("Policy %s activated", policy.id)
            else:
                policy.status = PolicyStatus.payment_failed
                logger.warning("STK payment failed for policy %s: code %s", policy.id, result_code)
            await db.commit()
    except Exception as e:
        logger.error("STK callback parse error: %s", e)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/b2c-callback")
async def b2c_callback(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    logger.info("B2C callback: %s", body)

    try:
        result = body["Result"]
        conv_id = result["ConversationID"]
        result_code = result["ResultCode"]

        payout = (await db.execute(
            select(Payout).where(Payout.mpesa_conversation_id == conv_id)
        )).scalars().first()

        if payout:
            if result_code == 0:
                payout.status = PayoutStatus.completed
                payout.completed_at = datetime.utcnow()
                items = {i["Key"]: i.get("Value") for i in result.get("ResultParameters", {}).get("ResultParameter", [])}
                payout.mpesa_transaction_id = str(items.get("TransactionID", ""))
                logger.info("Payout %s completed", payout.id)
            else:
                payout.status = PayoutStatus.failed
                logger.warning("B2C failed for payout %s: code %s", payout.id, result_code)
            await db.commit()
    except Exception as e:
        logger.error("B2C callback parse error: %s", e)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/b2c-timeout")
async def b2c_timeout(request: Request):
    logger.warning("B2C timeout received")
    return {"ResultCode": 0, "ResultDesc": "Accepted"}
