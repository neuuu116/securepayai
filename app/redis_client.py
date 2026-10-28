"""
Redis operations: OTP storage with auto-expiry, rate-limiting.

OTP codes are cryptographically generated (secrets, not random).
Rate limiting is atomic (INCR first, check second) to prevent brute-force bypass.
"""

import hmac
import secrets

import redis

from app.config import settings

r = redis.from_url(settings.redis_url, decode_responses=True)


def _otp_key(transaction_id: str) -> str:
    """Redis key for OTP code."""
    return f"otp:{transaction_id}"


def _attempts_key(transaction_id: str) -> str:
    """Redis key for attempt counter."""
    return f"otp_attempts:{transaction_id}"


def generate_and_store_otp(transaction_id: str) -> str:
    """
    Generate 6-digit OTP and store in Redis with TTL.
    Called by kafka_consumer when decision is FLAGGED.

    Uses secrets (CSPRNG), not random. Resets the attempts counter
    so a fresh OTP starts with fresh attempts.

    Returns: OTP code (as string, e.g., "034782")
    """
    code = f"{secrets.randbelow(1_000_000):06d}"
    pipe = r.pipeline()
    pipe.setex(_otp_key(transaction_id), settings.otp_ttl_seconds, code)
    pipe.delete(_attempts_key(transaction_id))  # Reset attempts for fresh OTP
    pipe.execute()
    return code


def verify_otp(transaction_id: str, submitted_code: str) -> tuple[bool, str]:
    """
    Verify submitted OTP against stored code.
    Implements rate limiting and expiry checks.

    Contract:
      - INCR attempt counter FIRST (atomic)
      - Check limit SECOND
      This prevents N parallel requests from all reading "0 attempts" and bypassing the limit.

    Args:
        transaction_id: Transaction being verified
        submitted_code: User-submitted code

    Returns:
        (success: bool, message: str)
    """
    # Check if OTP still exists (not expired)
    stored_code = r.get(_otp_key(transaction_id))
    if stored_code is None:
        return False, "OTP expired or never issued."

    # Increment attempt counter atomically + expire in one transaction
    pipe = r.pipeline()
    pipe.incr(_attempts_key(transaction_id))
    pipe.expire(_attempts_key(transaction_id), settings.otp_ttl_seconds)
    attempts, _ = pipe.execute()

    # Check rate limit AFTER increment
    if attempts > settings.otp_max_attempts:
        r.delete(_otp_key(transaction_id))  # Lock out: this OTP is dead now
        return False, "Too many attempts. Transaction blocked."

    # Constant-time comparison (no timing side channel)
    if hmac.compare_digest(submitted_code, stored_code):
        r.delete(_otp_key(transaction_id), _attempts_key(transaction_id))
        return True, "Verified successfully."

    # Count remaining attempts
    remaining = settings.otp_max_attempts - attempts
    return False, f"Incorrect code. {remaining} attempt(s) remaining."
