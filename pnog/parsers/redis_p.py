from datetime import datetime, timezone
from consumer.schema import CanonicalEvent

def parse(data: dict) -> CanonicalEvent | None:
    try:
        hit = data.get("cache_hit", False)
        return CanonicalEvent(
            layer      = 4,
            layer_name = "cache",
            node_id    = f"redis:{data.get('key', 'unknown')}",
            event_type = "cache_hit" if hit else "cache_miss",
            timestamp  = datetime.now(timezone.utc),
            severity   = "WARN" if not hit else "INFO",
            payload    = data,
            source     = "redis",
            node_type  = "CACHE_OP",
        )
    except Exception:
        return None
