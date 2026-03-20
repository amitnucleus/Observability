"""
Fault: Cache miss storm (thundering herd)
Symptoms: Redis hit rate drops to 0, CPU spike on app servers
PNOG traces: cache nodes weight spikes → resource metric anomaly → TTL config
"""
import redis
import time
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL)

print("[FAULT] Flushing Redis cache to trigger miss storm...")
r.flushdb()
print("[FAULT] Cache cleared. Every upload request will now miss cache.")
print("[FAULT] Watch PNOG: cache.events topic will show all misses.")
print("[FAULT] Observation weights on CacheEvent nodes will spike.")

# Simulate rapid requests that all miss cache
for i in range(30):
    key = f"upload:test_file_{i}.csv"
    val = r.get(key)
    print(f"  GET {key} → {'HIT' if val else 'MISS'}")
    time.sleep(0.1)

print("[FAULT] Done. Check PNOG anomalies endpoint for cache layer nodes.")
