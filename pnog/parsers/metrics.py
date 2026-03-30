from datetime import datetime, timezone
from consumer.schema import CanonicalEvent

def parse(data: dict) -> CanonicalEvent | None:
    try:
        metric   = data.get("metric", "unknown")
        value    = float(data.get("value", 0))
        severity = "ERROR" if value > 95 else "WARN" if value > 80 else "INFO"
        return CanonicalEvent(
            layer      = 7,
            layer_name = "resources",
            node_id    = f"metrics:{metric}:{data.get('host', 'host')}",
            event_type = "metric_sample",
            timestamp  = datetime.now(timezone.utc),
            severity   = severity,
            payload    = data,
            source     = "prometheus",
            node_type  = "RESOURCE_METRIC",
        )
    except Exception:
        return None
