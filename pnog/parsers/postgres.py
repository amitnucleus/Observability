from datetime import datetime, timezone
from consumer.schema import CanonicalEvent

def parse(data: dict) -> CanonicalEvent | None:
    try:
        operation  = data.get("operation", "QUERY")
        table      = data.get("table", "unknown")
        latency    = float(data.get("latency_ms", 0))
        severity   = "WARN" if latency > 1000 else "ERROR" if "fail" in data.get("event","") else "INFO"
        return CanonicalEvent(
            layer      = 3,
            layer_name = "database",
            node_id    = f"postgres:{table}:{operation}",
            event_type = data.get("event", "db_query"),
            timestamp  = datetime.now(timezone.utc),
            severity   = severity,
            payload    = data,
            source     = "postgres",
        )
    except Exception:
        return None
