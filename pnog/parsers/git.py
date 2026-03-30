from datetime import datetime, timezone
from consumer.schema import CanonicalEvent

def parse(data: dict) -> CanonicalEvent | None:
    try:
        return CanonicalEvent(
            layer      = 5,
            layer_name = "git",
            node_id    = f"git:{data.get('repo', 'unknown')}:{data.get('commit', 'unknown')[:8]}",
            event_type = data.get("event", "push"),
            timestamp  = datetime.now(timezone.utc),
            severity   = "INFO",
            payload    = data,
            source     = "git-webhook",
            node_type  = "RELEASE_SNAPSHOT",
        )
    except Exception:
        return None
