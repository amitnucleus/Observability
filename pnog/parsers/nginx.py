from datetime import datetime, timezone
from consumer.schema import CanonicalEvent

def parse(data: dict) -> CanonicalEvent | None:
    try:
        latency = float(data.get("request_time", 0))
        status  = int(data.get("status", 200))
        return CanonicalEvent(
            layer      = 0,
            layer_name = "network",
            node_id    = f"nginx:{data.get('uri', '/')}",
            event_type = "http_request",
            timestamp  = datetime.now(timezone.utc),
            severity   = "ERROR" if status >= 500 else "WARN" if status >= 400 else "INFO",
            payload    = data,
            source     = "nginx",
        )
    except Exception:
        return None
