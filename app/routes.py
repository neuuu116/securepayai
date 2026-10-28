"""
Two endpoints only, intentionally minimal for the demo:
  POST /transaction    - submit a transaction, gets pushed to Kafka
  GET /transaction/{id}/status - poll for fraud decision
  POST /verify-otp     - submit an OTP code for a flagged transaction

The API layer stays "dumb" - it validates input and publishes to
Kafka. All the actual decision logic lives in fraud_engine.py and
runs in the consumer. This separation is worth explaining clearly
in your pitch: API and fraud engine can scale independently.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from kafka.errors import KafkaError
from sqlalchemy.orm import Session

from app.db import FraudAnalysisRow, VerificationEventRow, get_db
from app.kafka_producer import publish_transaction
from app.models import OTPVerifyRequest, Transaction, TransactionIn
from app.redis_client import verify_otp

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transaction", status_code=202)
def submit_transaction(txn_in: TransactionIn):
    """
    Submit a transaction for fraud processing.
    Returns 202 Accepted (async processing).
    """
    txn = Transaction(
        transaction_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        **txn_in.model_dump(),
    )

    try:
        # mode="json" converts datetime -> ISO string for JSON serialization
        publish_transaction(txn.model_dump(mode="json"))
    except KafkaError:
        logger.exception("Kafka publish failed for %s", txn.transaction_id)
        raise HTTPException(
            status_code=503,
            detail="Could not queue transaction. Please retry.",
        )

    return {
        "transaction_id": txn.transaction_id,
        "status": "submitted",
        "message": f"Poll GET /transaction/{txn.transaction_id}/status for the decision.",
    }


@router.get("/transaction/{transaction_id}/status")
def transaction_status(transaction_id: str, db: Session = Depends(get_db)):
    """
    Poll for fraud decision.
    Returns "processing" if not yet in DB, otherwise the decision + details.
    """
    row = db.get(FraudAnalysisRow, transaction_id)
    if row is None:
        # Not in DB yet: either still in Kafka or the id is wrong
        return {"transaction_id": transaction_id, "status": "processing"}
    return {
        "transaction_id": transaction_id,
        "status": row.decision,  # "approved", "flagged", "blocked"
        "score": row.score,
        "reasons": row.reasons,
        "explanation": row.explanation,
        "otp_required": row.decision == "flagged",
    }


@router.post("/verify-otp")
def verify_transaction_otp(req: OTPVerifyRequest, db: Session = Depends(get_db)):
    """
    Verify OTP for a flagged transaction.
    Gate on DB verdict first for clear error messages (404, 409, 400).
    """
    # Check fraud verdict first: gives a clear error instead of
    # a misleading "OTP expired" for approved/blocked/unknown transactions
    row = db.get(FraudAnalysisRow, req.transaction_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found or still processing.",
        )
    if row.decision != "flagged":
        raise HTTPException(
            status_code=409,
            detail=f"Transaction is '{row.decision}'; OTP verification does not apply.",
        )

    # Verify the OTP
    success, message = verify_otp(req.transaction_id, req.otp_code)

    # Audit trail of every verification attempt
    db.add(VerificationEventRow(
        id=str(uuid.uuid4()),
        transaction_id=req.transaction_id,
        success=success,
    ))
    db.commit()

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "transaction_id": req.transaction_id,
        "status": "verified",
        "message": message,
    }
