import os
import json
from datetime import datetime, timezone
import structlog

log = structlog.get_logger()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "").strip()
DISABLE_KAFKA = os.getenv("DISABLE_KAFKA", "").strip().lower() in ("1", "true", "yes", "on")

_producer = None

def _try_get_producer():
    global _producer
    if DISABLE_KAFKA or not KAFKA_BROKER:
        return None

    if _producer is None:
        try:
            from confluent_kafka import Producer  # type: ignore
        except Exception as e:
            log.warning("kafka_disabled_missing_dependency", error=str(e))
            return None
        _producer = Producer({"bootstrap.servers": KAFKA_BROKER})
    return _producer

def publish(topic: str, payload: dict):
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    p = _try_get_producer()
    if p is None:
        # No-op when Kafka is disabled; keep app functional without Kafka.
        return
    p.produce(topic, json.dumps(payload).encode("utf-8"))
    p.poll(0)
