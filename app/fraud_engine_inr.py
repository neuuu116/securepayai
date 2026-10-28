"""
SecurePayAI - Indian Rupee Edition
Fraud Detection Engine optimized for UPI & Indian Banking Patterns
"""

from datetime import datetime
from typing import Tuple, List, Dict, Any
from app.config import settings

# ========== INR-SPECIFIC FRAUD DETECTION RULES ==========

# Rule Weights (Sum = 1.0 for normalized scoring)
RULE_WEIGHT_LARGE_AMOUNT = 0.40      # High multiple of user average
RULE_WEIGHT_NEW_DEVICE = 0.30        # Unknown device/UPI app
RULE_WEIGHT_NIGHT_TRANSACTION = 0.20 # Off-hours (00:00-05:00 IST)
RULE_WEIGHT_ROUND_AMOUNT = 0.10      # Structured ₹5000 multiples

# INR-Specific Thresholds
INR_LARGE_MULTIPLIER = 5.0            # Transaction >= 5x user average
INR_NIGHT_START_HOUR = 0              # Midnight IST
INR_NIGHT_END_HOUR = 5                # 5 AM IST
INR_ROUND_THRESHOLD = 25000           # ₹25,000 minimum for round check
INR_ROUND_MULTIPLE = 5000             # Multiples of ₹5,000

# UPI-Specific Risk Patterns
UPI_HIGH_VALUE_THRESHOLD = 100000     # ₹1,00,000 per transaction (RBI limit warning)
UPI_DAILY_LIMIT_WARNING = 300000      # ₹3,00,000 per day (typical NPCI threshold)
UPI_VELOCITY_THRESHOLD = 5            # More than 5 txns in 5 minutes = risky


def _is_night_transaction(ts: datetime) -> bool:
    """Check if transaction is in dormant night window (00:00-05:00 IST)."""
    return INR_NIGHT_START_HOUR <= ts.hour < INR_NIGHT_END_HOUR


def _is_suspiciously_round(amount: float) -> bool:
    """Check if amount is structured round value (common in fraud/testing)."""
    return (amount >= INR_ROUND_THRESHOLD and 
            amount % INR_ROUND_MULTIPLE == 0)


def _is_high_velocity(user_id: str, recent_transactions: List[Dict]) -> bool:
    """
    Check if user made multiple transactions in short timeframe.
    Common fraud pattern: rapid-fire small transactions to avoid detection.
    """
    if not recent_transactions:
        return False
    
    # Count transactions in last 5 minutes
    now = datetime.utcnow()
    recent_count = sum(1 for tx in recent_transactions 
                      if (now - tx.get('timestamp')).total_seconds() < 300)
    
    return recent_count >= UPI_VELOCITY_THRESHOLD


def score_transaction(
    transaction: Dict[str, Any],
    user_profile: Dict[str, Any] = None,
    recent_transactions: List[Dict] = None
) -> Tuple[float, List[str], Dict[str, Any]]:
    """
    Calculate fraud risk score for Indian UPI/banking transactions.
    
    Args:
        transaction: Payment details
        user_profile: User's historical data
        recent_transactions: Last N transactions for velocity check
    
    Returns:
        (score: 0.0-1.0, reasons: list, metadata: dict)
    """
    score = 0.0
    reasons: List[str] = []
    metadata = {
        "amount_inr": transaction.get("amount"),
        "upi_id": transaction.get("upi_id"),
        "device_type": transaction.get("device_type"),
        "timestamp_ist": transaction.get("timestamp"),
    }

    amount = float(transaction.get("amount", 0))
    user_avg = float(user_profile.get("avg_amount", 1000) if user_profile else 1000)
    is_new_device = bool(transaction.get("is_new_device", False))
    is_new_upi = bool(transaction.get("is_new_upi_app", False))
    
    try:
        tx_time = datetime.fromisoformat(transaction.get("timestamp", ""))
    except:
        tx_time = datetime.utcnow()

    # ===== RULE 1: Large Amount Relative to User Average (Weight: 0.40) =====
    if user_avg > 0:
        multiplier = amount / user_avg
        if multiplier >= INR_LARGE_MULTIPLIER:
            score += RULE_WEIGHT_LARGE_AMOUNT
            reasons.append(
                f"LARGE_AMOUNT: Amount ₹{amount:,.0f} is {multiplier:.1f}x user's average (₹{user_avg:,.0f})"
            )

    # ===== RULE 2: Unrecognized Device or UPI App (Weight: 0.30) =====
    if is_new_device or is_new_upi:
        score += RULE_WEIGHT_NEW_DEVICE
        device_info = "unknown device"
        if is_new_upi:
            device_info = "new UPI app installation"
        reasons.append(f"NEW_DEVICE: Transaction from {device_info}")

    # ===== RULE 3: Dormant Night Window (Weight: 0.20) =====
    if _is_night_transaction(tx_time):
        score += RULE_WEIGHT_NIGHT_TRANSACTION
        reasons.append(
            f"NIGHT_TRANSACTION: Initiated at {tx_time.strftime('%H:%M %p')} IST (off-hours risk)"
        )

    # ===== RULE 4: Round-Amount Structured Pattern (Weight: 0.10) =====
    if _is_suspiciously_round(amount):
        score += RULE_WEIGHT_ROUND_AMOUNT
        reasons.append(
            f"ROUND_AMOUNT: Structured sum ₹{amount:,.0f} (common in test/fraud)"
        )

    # ===== BONUS RULE: High Velocity Transactions (Weight: +0.15) =====
    if _is_high_velocity(transaction.get("user_id"), recent_transactions or []):
        score += min(0.15, 1.0 - score)  # Add up to 0.15, don't exceed 1.0
        reasons.append("HIGH_VELOCITY: Multiple transactions in 5 minutes detected")

    # ===== UPI-SPECIFIC WARNINGS (Non-blocking, informational) =====
    if amount > UPI_HIGH_VALUE_THRESHOLD:
        metadata["upi_warning"] = f"High value: ₹{amount:,.0f} exceeds typical single transaction"
    
    if user_profile and user_profile.get("daily_total", 0) + amount > UPI_DAILY_LIMIT_WARNING:
        metadata["daily_warning"] = "Daily transaction limit warning exceeded"

    # Normalize score to 0.0 - 1.0 range
    final_score = min(round(score, 2), 1.0)
    
    return final_score, reasons, metadata


def decide(score: float) -> str:
    """
    Route transaction based on risk score.
    
    INR-Specific Decision Thresholds:
    - Score < 0.30: APPROVED (fast-path, sub-50ms)
    - 0.30 ≤ Score < 0.60: FLAGGED (requires OTP/2FA)
    - Score ≥ 0.60: BLOCKED (immediate halt, regulatory hold)
    """
    if score >= 0.60:
        return "BLOCKED"
    elif score >= 0.30:
        return "FLAGGED"
    else:
        return "APPROVED"


# ========== UPI VALIDATION HELPERS ==========

def validate_upi_id(upi_id: str) -> bool:
    """
    Validate UPI ID format (handles: user@upi, user@bank, mobile@upi)
    Valid examples: 9876543210@okhdfcbank, user@googleplay, 98765@airtel
    """
    if not upi_id or "@" not in upi_id:
        return False
    
    parts = upi_id.split("@")
    if len(parts) != 2:
        return False
    
    username, provider = parts
    
    # Username: alphanumeric, dots, hyphens, underscores, or 10-digit mobile
    if not (username.replace(".", "").replace("-", "").replace("_", "").isalnum()):
        return False
    
    # Known UPI providers
    valid_providers = [
        "okhdfcbank", "okaxis", "okicici", "ybl", "okbankofbaroda",
        "upi", "googleplay", "airtel", "apl", "allbank", "aubank",
        "dbs", "hsbc", "ibl", "indus", "kotak", "pnb", "postbank",
        "sbi", "unionbank", "united", "airtelpaymentsbank", "aubank",
        "dbs", "fbl", "federal", "idfcbank"
    ]
    
    return provider.lower() in valid_providers


def get_otp_message_template_inr(upi_id: str, amount: float, merchant: str) -> str:
    """Generate OTP message for flagged INR transaction."""
    return (
        f"SecurePayAI: Verify transaction of ₹{amount:,.0f} to {merchant} "
        f"from {upi_id}. Reply with 6-digit OTP to confirm. Never share OTP."
    )


# ========== TRANSACTION METADATA ENRICHMENT ==========

def enrich_transaction_metadata(transaction: Dict) -> Dict:
    """Enrich transaction with INR-specific metadata."""
    enriched = transaction.copy()
    enriched["currency"] = "INR"
    enriched["timezone"] = "Asia/Kolkata"  # IST
    enriched["payment_method"] = "UPI"
    
    # Add transaction timestamp if missing
    if "timestamp" not in enriched:
        enriched["timestamp"] = datetime.now(tz=None).isoformat()
    
    return enriched
