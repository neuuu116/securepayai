"""
Fraud scoring engine - rule-based, explainable decisions.
Each rule independently adds weight to score.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.models import Decision, Transaction

# Local timezone for fraud rule evaluation
LOCAL_TZ = ZoneInfo("Asia/Kolkata")

# Rule weights (sum to 1.0)
RULE_WEIGHT_LARGE_AMOUNT = 0.4
RULE_WEIGHT_NEW_DEVICE = 0.3
RULE_WEIGHT_NIGHT_TXN = 0.2
RULE_WEIGHT_ROUND_AMOUNT = 0.1


def _local(ts: datetime) -> datetime:
    """Convert timestamp to local time. Handles both naive and aware."""
    return ts.astimezone(LOCAL_TZ) if ts.tzinfo else ts


def _is_night_transaction(ts: datetime) -> bool:
    """Check if transaction occurred during night hours (local time)."""
    local_ts = _local(ts)
    return settings.fraud_night_start_hour <= local_ts.hour < settings.fraud_night_end_hour


def _is_suspiciously_round(amount: float) -> bool:
    """Exact multiples of 1000 >= 5000 are suspicious (e.g., 50000.00)."""
    return amount % 1000 == 0 and amount >= 5000


def score_transaction(txn: Transaction) -> tuple[float, list[str]]:
    """
    Returns: (score 0.0–1.0, list of human-readable reasons)
    
    Each rule independently adds to score. No interactions.
    Score is capped at 1.0.
    """
    score = 0.0
    reasons: list[str] = []

    # Rule 1: Large amount (> 5x user average)
    if txn.user_avg_transaction_amount > 0:
        multiplier = txn.amount / txn.user_avg_transaction_amount
        if multiplier >= settings.fraud_amount_multiplier:
            score += RULE_WEIGHT_LARGE_AMOUNT
            reasons.append(f"amount is {multiplier:.1f}x user's average")

    # Rule 2: New device
    if txn.is_new_device:
        score += RULE_WEIGHT_NEW_DEVICE
        reasons.append("transaction from a new/unrecognized device")

    # Rule 3: Night transaction (local time)
    if _is_night_transaction(txn.timestamp):
        score += RULE_WEIGHT_NIGHT_TXN
        local_ts = _local(txn.timestamp)
        reasons.append(
            f"occurred at {local_ts.strftime('%H:%M')} "
            f"(during {settings.fraud_night_start_hour}:00-{settings.fraud_night_end_hour}:00 window)"
        )

    # Rule 4: Suspiciously round amount
    if _is_suspiciously_round(txn.amount):
        score += RULE_WEIGHT_ROUND_AMOUNT
        reasons.append("suspiciously round transaction amount")

    return min(score, 1.0), reasons


def decide(score: float) -> Decision:
    """Map fraud score to decision threshold."""
    if score >= 0.7:
        return Decision.BLOCKED     # Too risky, hard reject
    if score >= 0.3:
        return Decision.FLAGGED     # Suspicious, needs OTP
    return Decision.APPROVED        # Safe to proceed
