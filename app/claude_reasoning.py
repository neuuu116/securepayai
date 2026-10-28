import logging

from app.config import settings
from app.models import Transaction

logger = logging.getLogger(__name__)

_client = None


def _template(reasons: list[str], score: float) -> str:
    """Fallback explanation template."""
    return f"Transaction flagged with risk score {score:.2f}. Triggered rules: {', '.join(reasons)}"


def _get_client():
    """Lazy load Anthropic client. Missing SDK won't crash the app."""
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=settings.anthropic_api_key, max_retries=1)
    return _client


def explain_flagged_transaction(txn: Transaction, reasons: list[str], score: float) -> str:
    """
    Generate explanation for flagged/blocked transaction.
    NEVER raises. Any failure falls back to template.
    The fraud decision comes from the rule engine, not the LLM.
    """
    fallback = _template(reasons, score)

    if not settings.anthropic_api_key:
        return fallback

    prompt = (
        "You are a fraud analyst assistant. In 2 short sentences, explain to a "
        "customer why this payment needs extra checks. Use ONLY the facts below, "
        "do not invent details, do not accuse the customer of fraud.\n\n"
        f"Amount: {txn.amount}\n"
        f"Merchant: {txn.merchant}\n"
        f"Risk score (0-1): {score:.2f}\n"
        f"Triggered rules: {'; '.join(reasons)}"
    )

    try:
        msg = _get_client().messages.create(
            model=settings.anthropic_model,
            max_tokens=200,
            timeout=8.0,  # Slow LLM must not stall the consumer
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        return text or fallback
    except Exception:
        logger.warning("Claude explanation failed, using template", exc_info=True)
        return fallback
