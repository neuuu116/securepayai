"""
Kafka consumer - standalone worker process for fraud scoring.

Run as: python -m app.kafka_consumer

Reads from raw-transactions, scores each transaction, persists results to Postgres,
generates OTPs for flagged transactions, and publishes decisions to output topics.
"""

import json
import logging
import signal

from kafka import KafkaConsumer, KafkaProducer
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.claude_reasoning import explain_flagged_transaction
from app.config import settings
from app.db import FraudAnalysisRow, SessionLocal, TransactionRow, init_db
from app.fraud_engine import decide, score_transaction
from app.models import Decision, Transaction
from app.redis_client import generate_and_store_otp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("consumer")

OUTPUT_TOPICS = {
    Decision.APPROVED: "approved-transactions",
    Decision.FLAGGED: "flagged-transactions",
    Decision.BLOCKED: "blocked-transactions",
}


def _deserialize(raw: bytes) -> dict | None:
    """
    Bad JSON must not crash the consumer loop; return None and skip it.
    """
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.error("Skipping undecodable message: %r", raw[:200])
        return None


def deliver_otp(txn: Transaction, code: str) -> None:
    """
    MOCK delivery. Replace with SMS/email (Twilio, SES...) later.
    Never log OTPs in production; this is for local demo only.
    """
    logger.info("[MOCK SMS] user=%s txn=%s OTP=%s", txn.user_id, txn.transaction_id, code)


def process_message(txn_dict: dict, producer: KafkaProducer) -> None:
    """
    Contract with the run() loop:
      - returns normally  -> safe to commit the offset
        (processed OK, duplicate, or permanently bad message)
      - raises            -> offset NOT committed, message is redelivered
    """
    # 1. Parse. A malformed message will NEVER succeed, so skip it
    try:
        txn = Transaction(**txn_dict)
    except ValidationError as e:
        logger.error("Invalid transaction payload, skipping: %s", e)
        return

    # 2. Score + decide
    score, reasons = score_transaction(txn)
    decision = decide(score)

    # 3. Explanation for risky cases. explain_flagged_transaction never raises
    explanation = None
    if decision in (Decision.FLAGGED, Decision.BLOCKED):
        explanation = explain_flagged_transaction(txn, reasons, score)

    # 4. Persist. transaction_id is PRIMARY KEY, so a replayed message
    #    raises IntegrityError = idempotency for free.
    db = SessionLocal()
    try:
        db.add(TransactionRow(
            transaction_id=txn.transaction_id,
            user_id=txn.user_id,
            amount=txn.amount,
            merchant=txn.merchant,
            device_id=txn.device_id,
            is_new_device=txn.is_new_device,
            timestamp=txn.timestamp,
        ))
        db.add(FraudAnalysisRow(
            transaction_id=txn.transaction_id,
            score=score,
            decision=decision.value,
            reasons=", ".join(reasons) if reasons else "none",
            explanation=explanation,
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.warning("Duplicate transaction %s, already processed. Skipping.", txn.transaction_id)
        return
    except Exception:
        db.rollback()
        raise  # Real failure -> do not commit offset, retry later
    finally:
        db.close()

    # 5. OTP only for FLAGGED, and only AFTER the DB commit succeeded.
    #    BLOCKED = hard reject, no OTP (design decision).
    if decision == Decision.FLAGGED:
        code = generate_and_store_otp(txn.transaction_id)
        deliver_otp(txn, code)

    # 6. Publish the decision
    producer.send(OUTPUT_TOPICS[decision], key=txn.user_id.encode(), value={
        "transaction_id": txn.transaction_id,
        "decision": decision.value,
        "score": score,
    })

    logger.info("%s -> %s (score=%.2f)", txn.transaction_id, decision.value, score)


def _stop(*_):
    """Signal handler for graceful shutdown."""
    raise KeyboardInterrupt


def run() -> None:
    """Run as: python -m app.kafka_consumer"""
    init_db()

    consumer = KafkaConsumer(
        "raw-transactions",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_deserializer=_deserialize,
        group_id="fraud-engine-workers",
        auto_offset_reset="earliest",   # New group reads from the start, nothing skipped
        enable_auto_commit=False,       # WE decide when a message counts as done
    )
    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        key_serializer=lambda k: k,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        retries=5,
    )

    signal.signal(signal.SIGTERM, _stop)  # docker stop / kill -> clean shutdown
    logger.info("Consumer started, listening on raw-transactions...")

    try:
        for message in consumer:
            if message.value is not None:
                process_message(message.value, producer)
            producer.flush(timeout=10)  # Decision is on the broker...
            consumer.commit()           # ...THEN mark the input message as done
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    except Exception:
        logger.exception("Fatal error; exiting so the supervisor restarts us")
        raise
    finally:
        consumer.close()
        producer.flush(timeout=10)
        producer.close()


if __name__ == "__main__":
    run()
