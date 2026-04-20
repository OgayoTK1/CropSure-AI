"""
M-Pesa Daraja callback endpoints.

POST /webhooks/stk-callback   — STK Push payment result
POST /webhooks/b2c-result     — B2C payout result
POST /webhooks/b2c-timeout    — B2C payout timeout
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import MpesaTransaction

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stk-callback")
async def stk_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Safaricom calls this after an STK Push completes (success or failure).
    Updates the corresponding MpesaTransaction record.
    """
    body = await request.json()
    logger.info("STK callback received: %s", body)

    try:
        callback = body["Body"]["stkCallback"]
        checkout_request_id = callback["CheckoutRequestID"]
        result_code = int(callback["ResultCode"])

        result = await db.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.checkout_request_id == checkout_request_id
            )
        )
        tx = result.scalar_one_or_none()

        if tx:
            if result_code == 0:
                # Extract receipt from CallbackMetadata
                items = {
                    item["Name"]: item.get("Value")
                    for item in callback.get("CallbackMetadata", {}).get("Item", [])
                }
                tx.mpesa_receipt_number = str(items.get("MpesaReceiptNumber", ""))
                tx.status = "success"
            else:
                tx.status = "failed"
            tx.updated_at = datetime.utcnow()
    except (KeyError, TypeError) as exc:
        logger.error("STK callback parse error: %s | body: %s", exc, body)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/b2c-result")
async def b2c_result(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Safaricom calls this after a B2C payment completes.
    Updates the corresponding MpesaTransaction record.
    """
    body = await request.json()
    logger.info("B2C result received: %s", body)

    try:
        result_body = body["Result"]
        conversation_id = result_body["ConversationID"]
        result_code = int(result_body["ResultCode"])

        result = await db.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.conversation_id == conversation_id
            )
        )
        tx = result.scalar_one_or_none()

        if tx:
            if result_code == 0:
                params = {
                    p["Key"]: p["Value"]
                    for p in result_body.get("ResultParameters", {}).get("ResultParameter", [])
                }
                tx.mpesa_receipt_number = str(params.get("TransactionReceipt", ""))
                tx.status = "success"
            else:
                tx.status = "failed"
            tx.updated_at = datetime.utcnow()
    except (KeyError, TypeError) as exc:
        logger.error("B2C result parse error: %s | body: %s", exc, body)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}


@router.post("/b2c-timeout")
async def b2c_timeout(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Safaricom calls this when a B2C request times out in the queue.
    Marks the transaction as null/failed so it can be retried.
    """
    body = await request.json()
    logger.warning("B2C timeout received: %s", body)

    try:
        conversation_id = body["Result"]["ConversationID"]
        result = await db.execute(
            select(MpesaTransaction).where(
                MpesaTransaction.conversation_id == conversation_id
            )
        )
        tx = result.scalar_one_or_none()
        if tx:
            tx.status = "failed"
            tx.updated_at = datetime.utcnow()
    except (KeyError, TypeError) as exc:
        logger.error("B2C timeout parse error: %s | body: %s", exc, body)

    return {"ResultCode": 0, "ResultDesc": "Accepted"}
