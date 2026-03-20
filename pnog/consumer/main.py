import os
import json
import structlog
from confluent_kafka import Consumer, KafkaError
from consumer.router import route

log = structlog.get_logger()

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

TOPICS = [
    "net.requests",
    "app.events",
    "pod.logs",
    "db.queries",
    "cache.events",
    "git.releases",
    "frontend.errors",
    "metrics.resources",
]

def run():
    c = Consumer({
        "bootstrap.servers":  KAFKA_BROKER,
        "group.id":           "pnog-monitor",
        "auto.offset.reset":  "latest",
        "enable.auto.commit": True,
    })
    c.subscribe(TOPICS)
    log.info("pnog_consumer_started", topics=TOPICS)

    try:
        while True:
            msg = c.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                log.error("kafka_error", error=str(msg.error()))
                continue

            try:
                data  = json.loads(msg.value().decode("utf-8"))
                topic = msg.topic()
                route(topic, data)
            except Exception as e:
                log.error("event_processing_error", error=str(e))

    finally:
        c.close()

if __name__ == "__main__":
    run()
