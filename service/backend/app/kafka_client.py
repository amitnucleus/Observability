import os
import json
from datetime import datetime, timezone
from confluent_kafka import Producer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

_producer = None

def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({"bootstrap.servers": KAFKA_BROKER})
    return _producer

def publish(topic: str, payload: dict):
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    p = get_producer()
    p.produce(topic, json.dumps(payload).encode("utf-8"))
    p.poll(0)
