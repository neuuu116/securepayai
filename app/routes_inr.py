"""
INR-Specific Routes for SecurePayAI
Handles UPI transactions with fraud detection optimized for Indian market
"""

from fastapi import APIRouter, HTTPException
import uuid
from datetime import datetime

from app.fraud_engine_inr import (
    score_transaction, 
    decide, 
    validate_upi_id,
    enrich_transaction_metadata
)
from app.models import Decision
from app.kafka_producer import publish_transaction
from app.redis_client import verify_otp
from app.db import SessionLocal, TransactionRow, FraudAnalysisRow

router = APIRouter(prefix="/api/v1/inr", tags=["INR Payments"])


@router.post("/transaction-inr")
def submit_inr_transaction(payload: dict):
    """
    Submit an INR/UPI transaction for fraud detection.
    
    Expected fields:
    - upi_id: str (username@provider)
    - amount: float (₹1 - ₹100,000)
    - merchant: str
    - device_id: str
    - device_type: str (mobile/web)
    - is_new_device: bool
    - is_new_upi_app: bool
    - user_avg_transaction_amount: float
    - user_id: str
    """
    
    # Validate UPI ID
    upi_id = payload.get("upi_id", "").strip()
    if not validate_upi_id(upi_id):
        raise HTTPException(status_code=400, detail="Invalid UPI ID format")
    
    # Validate amount
    amount = float(payload.get("amount", 0))
    if amount <= 0 or amount > 100000:
        raise HTTPException(status_code=400, detail="Amount must be ₹1 - ₹100,000")
    
    # Enrich with metadata
    transaction = enrich_transaction_metadata({
        "transaction_id": str(uuid.uuid4()),
        "user_id": payload.get("user_id", "user-unknown"),
        "upi_id": upi_id,
        "amount": amount,
        "merchant": payload.get("merchant", "Unknown"),
        "device_id": payload.get("device_id"),
        "device_type": payload.get("device_type", "mobile"),
        "is_new_device": payload.get("is_new_device", False),
        "is_new_upi_app": payload.get("is_new_upi_app", False),
        "user_avg_transaction_amount": float(payload.get("user_avg_transaction_amount", 5000)),
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    # Calculate fraud score
    score, reasons, metadata = score_transaction(transaction)
    decision = decide(score)
    
    # Publish to Kafka for async processing
    publish_transaction({
        **transaction,
        "score": score,
        "decision": decision,
        "reasons": reasons,
        "metadata": metadata
    })
    
    return {
        "transaction_id": transaction["transaction_id"],
        "status": "submitted",
        "message": "INR transaction submitted for fraud analysis",
        "upi_id": upi_id,
        "amount_inr": amount,
        "merchant": payload.get("merchant")
    }


@router.post("/verify-otp-inr")
def verify_inr_transaction_otp(payload: dict):
    """
    Verify OTP for flagged INR transaction.
    
    Expected fields:
    - transaction_id: str
    - otp_code: str (6 digits)
    - upi_id: str
    """
    
    transaction_id = payload.get("transaction_id")
    otp_code = payload.get("otp_code")
    upi_id = payload.get("upi_id")
    
    if len(otp_code) != 6 or not otp_code.isdigit():
        raise HTTPException(status_code=400, detail="OTP must be 6 digits")
    
    success, message = verify_otp(transaction_id, otp_code)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Update transaction status in DB
    db = SessionLocal()
    try:
        fraud_record = db.query(FraudAnalysisRow).filter(
            FraudAnalysisRow.transaction_id == transaction_id
        ).first()
        
        if fraud_record:
            fraud_record.decision = "VERIFIED"
            db.commit()
    finally:
        db.close()
    
    return {
        "transaction_id": transaction_id,
        "upi_id": upi_id,
        "status": "verified",
        "message": "OTP verified successfully. Transaction confirmed.",
    }


@router.get("/transaction-inr/{transaction_id}/status")
def get_inr_transaction_status(transaction_id: str):
    """Get real-time status of an INR transaction."""
    
    db = SessionLocal()
    try:
        fraud_record = db.query(FraudAnalysisRow).filter(
            FraudAnalysisRow.transaction_id == transaction_id
        ).first()
        
        if not fraud_record:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {
            "transaction_id": transaction_id,
            "score": fraud_record.score,
            "decision": fraud_record.decision,
            "reasons": fraud_record.reasons,
            "explanation": fraud_record.explanation,
            "created_at": fraud_record.created_at.isoformat(),
        }
    finally:
        db.close()


@router.get("/upi/validate/{upi_id}")
def validate_upi_endpoint(upi_id: str):
    """Validate UPI ID format."""
    is_valid = validate_upi_id(upi_id)
    return {
        "upi_id": upi_id,
        "is_valid": is_valid,
        "message": "Valid UPI ID" if is_valid else "Invalid UPI ID format"
    }


@router.get("/limits/inr")
def get_inr_limits():
    """Get INR payment limits and thresholds."""
    return {
        "currency": "INR",
        "single_transaction_limit": 100000,
        "daily_limit_warning": 300000,
        "high_value_threshold": 100000,
        "round_amount_multiplier": 5000,
        "round_amount_minimum": 25000,
        "night_window_start": "00:00",
        "night_window_end": "05:00",
        "timezone": "Asia/Kolkata",
    }
