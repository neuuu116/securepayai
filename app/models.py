"""
Pydantic models = the "shape" of data moving through the API and Kafka.
These are NOT database models (that's db.py) - these are what
gets validated at the API boundary and serialized onto Kafka topics.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Decision(str, Enum):
    APPROVED = "approved"   # process normally
    FLAGGED = "flagged"     # OTP verification required
    BLOCKED = "blocked"     # hard reject, no OTP


class TransactionIn(BaseModel):
    """What the client sends us when a transaction happens."""
    user_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    merchant: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    is_new_device: bool = False
    user_avg_transaction_amount: float = Field(
        default=0.0,
        ge=0,
        description="Rolling average spend for this user - used by the fraud engine",
    )


class Transaction(TransactionIn):
    """Same as TransactionIn but with fields the server fills in."""
    transaction_id: str
    timestamp: datetime


class FraudResult(BaseModel):
    """Output of the fraud engine for one transaction."""
    transaction_id: str
    score: float          # 0.0 (safe) to 1.0 (definitely fraud)
    decision: Decision
    reasons: list[str]    # e.g. ["amount 8.2x average", "new device", "night transaction"]
    explanation: str | None = None  # filled in by Claude for flagged/blocked txns


class OTPVerifyRequest(BaseModel):
    transaction_id: str = Field(min_length=1)
    otp_code: str = Field(pattern=r"^\d{6}$")  # exactly 6 digits
