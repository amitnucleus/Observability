"""
Bridges Prometheus metrics → Kafka metrics.resources topic.
Runs as a sidecar, scraping Prometheus and publishing to PNOG.
"""
import os
import time
import json
import requests
from confluent_kafka import Producer

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
KAFKA_BROKER   = os.getenv("KAFKA_BROKER", "kafka:9092")
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "15"))

METRICS_TO_TRACK = [
    "node_cpu_seconds_total",
    "node_memory_MemAvailable_bytes",
    "node_filesystem_avail_bytes",
    "process_resident_memory_bytes",
]

producer = Producer({"bootstrap.servers": KAFKA_BROKER})

def scrape_metric(metric_name: str) -> list[dict]:
    try:
        res = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": metric_name},
            timeout=5,
        )
        data = res.json()
        results = []
        for r in data.get("data", {}).get("result", []):
            results.append({
                "metric": metric_name,
                "host":   r["metric"].get("instance", "unknown"),
                "value":  float(r["value"][1]),
                "labels": r["metric"],
            })
        return results
    except Exception as e:
        print(f"Error scraping {metric_name}: {e}")
        return []

def publish(payload: dict):
    producer.produce(
        "metrics.resources",
        json.dumps(payload).encode("utf-8"),
    )
    producer.poll(0)

def run():
    print(f"Prometheus→Kafka bridge started. Scraping every {SCRAPE_INTERVAL}s")
    while True:
        for metric in METRICS_TO_TRACK:
            for sample in scrape_metric(metric):
                publish({**sample, "layer": "L7"})
        producer.flush()
        time.sleep(SCRAPE_INTERVAL)

if __name__ == "__main__":
    run()
