"""
Listens to Redis keyspace notifications and publishes to Kafka cache.events topic.
Redis must be configured with: notify-keyspace-events KEA (already set in docker-compose)
"""
import os
import json
import redis
from confluent_kafka import Producer

REDIS_URL    = os.getenv("REDIS_URL", "redis://redis:6379/0")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

producer = Producer({"bootstrap.servers": KAFKA_BROKER})
r        = redis.from_url(REDIS_URL)
pubsub   = r.pubsub()

# Subscribe to all keyspace events
pubsub.psubscribe("__keyevent@0__:*")

print("Redis→Kafka cache bridge started")

def publish(payload: dict):
    producer.produce("cache.events", json.dumps(payload).encode("utf-8"))
    producer.poll(0)

for message in pubsub.listen():
    if message["type"] != "pmessage":
        continue
    try:
        channel = message["channel"].decode()
        key     = message["data"].decode()
        op      = channel.split(":")[-1]          # get, set, del, expired, etc.
        publish({
            "event":     f"cache_{op}",
            "key":       key,
            "operation": op,
            "cache_hit": op == "get",
            "layer":     "L4",
        })
    except Exception as e:
        print(f"Error processing Redis event: {e}")
