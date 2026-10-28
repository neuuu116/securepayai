"""
Kafka producer - publish transactions to the raw-transactions topic.
Called by the FastAPI routes.

Lazy loading: producer created only when first transaction arrives.
This way, if Kafka is down, the API still boots (only /transaction fails with 503).
"""

import json
import logging
import threading

from kafka import KafkaProducer

from app.config import settings

logger = logging.getLogger(__name__)

RAW_TOPIC = "raw-transactions"

_producer: KafkaProducer | None = None
_lock = threading.Lock()


def get_producer() -> KafkaProducer:
    """
    Lazy singleton. Creating the producer at import time meant the whole API
    crashed on startup whenever Kafka was down. Now the API boots fine and
    only /transaction fails (with a clean 503) until Kafka is back.
    """
    global _producer
    if _producer is None:
        with _lock:
            if _producer is None:
                _producer = KafkaProducer(
                    bootstrap_servers=settings.kafka_bootstrap_servers,
                    key_serializer=lambda k: k.encode("utf-8"),
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                    acks="all",              # Wait for broker to confirm the write
                    retries=5,               # Retry transient failures
                    request_timeout_ms=10_000,
                    max_block_ms=5_000,      # Don't hang 60s if broker unreachable
                )
    return _producer


def publish_transaction(txn_dict: dict) -> None:
    """
    Publish to raw-transactions and WAIT for the broker ack.
    Raises kafka.errors.KafkaError on failure so the route can return 503
    instead of telling the client "submitted" for a message that was lost.

    Key = user_id -> all transactions of one user land in the same partition,
    so they are processed in order.
    """
    future = get_producer().send(
        RAW_TOPIC,
        key=txn_dict["user_id"],
        value=txn_dict,
    )
    future.get(timeout=10)  # Wait for ack or raise


def close_producer() -> None:
    """Called on app shutdown: flush pending messages, then close."""
    global _producer
    if _producer is not None:
        try:
            _producer.flush(timeout=10)
        finally:
            _producer.close()
            _producer = None
