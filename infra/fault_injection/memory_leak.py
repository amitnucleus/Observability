"""
Fault: Memory leak in Celery worker pod
Layers: L2 Pod + L7 Resources
PNOG traces: PodEvent weight ↑ → ResourceMetric memory ↑ → batch_size config
"""
import time

print("[FAULT] Simulating memory leak in worker process...")
leak = []
try:
    for i in range(100):
        # Allocate ~1MB per iteration without releasing
        leak.append(" " * 1_000_000)
        mb = len(leak)
        print(f"  Allocated {mb}MB — watch L7 metrics.resources in PNOG")
        time.sleep(0.5)
        if mb >= 50:
            print("[FAULT] 50MB allocated. Holding for 10 seconds...")
            time.sleep(10)
            break
except MemoryError:
    print("[FAULT] OOM reached — pod would be killed here in K8s")
finally:
    del leak
    print("[FAULT] Memory released. Watch PNOG graph normalize.")
