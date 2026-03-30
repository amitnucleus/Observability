import structlog
from parsers import nginx, fastapi, pod, postgres, redis_p, git, browser, metrics
from graph.engine import get_graph

log = structlog.get_logger()

TOPIC_MAP = {
    "net.requests":    nginx.parse,
    "app.events":      fastapi.parse,
    "pod.logs":        pod.parse,
    "db.queries":      postgres.parse,
    "cache.events":    redis_p.parse,
    "git.releases":    git.parse,
    "frontend.errors": browser.parse,
    "metrics.resources": metrics.parse,
}

def route(topic: str, data: dict):
    parser = TOPIC_MAP.get(topic)
    if not parser:
        log.warn("no_parser_for_topic", topic=topic)
        return

    event = parser(data)
    if event is None:
        return

    g = get_graph()
    g.ingest(event)
    log.debug("event_ingested", layer=event.layer_name, node=event.node_id, evt=event.event_type)
