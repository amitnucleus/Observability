from datetime import datetime, timezone
from consumer.schema import CanonicalEvent

def parse(data: dict) -> CanonicalEvent | None:
    try:
        event_type = data.get("event", "pod_event")
        severity   = "ERROR" if "fail" in event_type else "INFO"
        return CanonicalEvent(
            layer      = 2,
            layer_name = "pod",
            node_id    = f"pod:{data.get('worker', 'celery')}:{data.get('job_id', 'unknown')}",
            event_type = event_type,
            timestamp  = datetime.now(timezone.utc),
            severity   = severity,
            payload    = data,
            source     = "celery",
        )
    except Exception:
        return None
