from datetime import datetime, timezone
from consumer.schema import CanonicalEvent

def parse(data: dict) -> CanonicalEvent | None:
    try:
        event_type = data.get("event", "app_event")
        severity   = "ERROR" if "fail" in event_type else "INFO"
        return CanonicalEvent(
            layer      = 1,
            layer_name = "application",
            node_id    = f"fastapi:{event_type}:{data.get('job_id', 'unknown')}",
            event_type = event_type,
            timestamp  = datetime.now(timezone.utc),
            severity   = severity,
            payload    = data,
            source     = "fastapi",
        )
    except Exception:
        return None
