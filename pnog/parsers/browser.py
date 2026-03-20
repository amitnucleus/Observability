from datetime import datetime, timezone
from consumer.schema import CanonicalEvent

def parse(data: dict) -> CanonicalEvent | None:
    try:
        return CanonicalEvent(
            layer      = 6,
            layer_name = "frontend",
            node_id    = f"browser:{data.get('error_type', 'unknown')}",
            event_type = data.get("event", "browser_error"),
            timestamp  = datetime.now(timezone.utc),
            severity   = "ERROR",
            payload    = data,
            source     = "sentry",
        )
    except Exception:
        return None
