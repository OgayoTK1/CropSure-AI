"""
M-Pesa Daraja callback endpoints (mounted at /mpesa).

POST /mpesa/stk-callback   — STK Push result → updates Policy status
POST /mpesa/b2c-callback   — B2C payout result → updates Payout status
POST /mpesa/b2c-timeout    — B2C queue timeout → marks Payout failed
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Policy, Payout, PolicyStatus, PayoutStatus

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stk-callback")
async def stk_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Safaricom posts here after STK Push completes.
    On success: sets Policy.status = active, stores receipt in mpesa_reference.
    On failure: sets Policy.status = payment_failed.
    """
    body = await request.json()
    logger.info("STK callback: %s", body)

    try:
        callback = body["Body"]["stkCallback"]
        checkout_request_id = callback["CheckoutRequestID"]
        result_code = int(callback["ResultCode"])

        result = await db.execute(
            select(Policy).where(Policy.mpesa_reference == checkout_request_id)
        )
        policy = result.scalar_one_or_none()

        if policy:
            if result_code == 0:
                items = {
                    item["Name"]: item.get("Value")
                    for item in callback.get("CallbackMetadata", {}).get("Item", [])
                }
                policy.mpesa_reference = str(items.get("MpesaReceiptNumber", checkout_request_id))
                policy.status = PolicyStatus.active
                logger.info("Policy %s activated via STK", policy.id)
            else:
                policy.status = PolicyStatus.payment_failed
                logger.warning("STK payment failed for policy %s (code %s)", policy.id, result_code)
        else:
            logger.warning("No policy found for CheckoutRequestID %s", checkout_request_id)

    except (KeyError, TypeError) as exc:
        logger.error("STK callback parse error: %s | body: %s", exc, body)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/b2c-callback")
async def b2c_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Safaricom posts here after B2C payout completes.
    On success: sets Payout.status = completed, records completed_at.
    On failure: sets Payout.status = failed (manual retry required).
    """
    body = await request.json()
    logger.info("B2C callback: %s", body)

    try:
        result_body = body["Result"]
        conversation_id = result_body["ConversationID"]
        result_code = int(result_body["ResultCode"])

        result = await db.execute(
            select(Payout).where(Payout.mpesa_transaction_id == conversation_id)
        )
        payout = result.scalar_one_or_none()

        if payout:
            if result_code == 0:
                payout.status = PayoutStatus.completed
                payout.completed_at = datetime.utcnow()
                logger.info("Payout %s completed (ConversationID %s)", payout.id, conversation_id)
            else:
                payout.status = PayoutStatus.failed
                logger.error(
                    "B2C payout %s failed (code %s): %s",
                    payout.id, result_code, result_body.get("ResultDesc"),
                )
        else:
            logger.warning("No payout found for ConversationID %s", conversation_id)

    except (KeyError, TypeError) as exc:
        logger.error("B2C callback parse error: %s | body: %s", exc, body)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/b2c-timeout")
async def b2c_timeout(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Safaricom posts here when a B2C request times out in the queue.
    Marks the payout as failed so it can be retried manually.
    """
    body = await request.json()
    logger.warning("B2C timeout: %s", body)

    try:
        conversation_id = body["Result"]["ConversationID"]
        result = await db.execute(
            select(Payout).where(Payout.mpesa_transaction_id == conversation_id)
        )
        payout = result.scalar_one_or_none()
        if payout:
            payout.status = PayoutStatus.failed
    except (KeyError, TypeError) as exc:
        logger.error("B2C timeout parse error: %s | body: %s", exc, body)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}
