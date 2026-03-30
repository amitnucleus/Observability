import math
import threading
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional
import networkx as nx
import structlog

from consumer.schema import CanonicalEvent

log = structlog.get_logger()

# ── Singleton graph instance ───────────────────────────────────
_graph_instance = None
_lock = threading.Lock()

def get_graph() -> "PNOGGraph":
    global _graph_instance
    if _graph_instance is None:
        with _lock:
            if _graph_instance is None:
                _graph_instance = PNOGGraph()
    return _graph_instance


class PNOGGraph:
    """
    Living probabilistic multi-layer property graph.

    Nodes carry:
        - layer, layer_name, event_type, severity
        - observation_weight: W(u,v,t) accumulated score
        - last_seen: timestamp of most recent event
        - event_count: total events seen on this node

    Edges carry:
        - co_occurrence_count: how many times both nodes fired in the same window
        - weight: W(u,v,t) score on the edge
        - last_co_occurrence: timestamp
    """

    CO_OCCURRENCE_WINDOW_SECONDS = 10
    DECAY_LAMBDA                 = 0.1   # recency decay rate
    ANOMALY_THRESHOLD            = 5.0   # W above this triggers RCA

    def __init__(self):
        self.G          = nx.DiGraph()
        self.timeline   = []             # (timestamp, node_id) — time-indexed universe
        self._lock      = threading.Lock()
        log.info("pnog_graph_initialized")

    # ── Ingest ─────────────────────────────────────────────────

    def ingest(self, event: CanonicalEvent):
        with self._lock:
            self._upsert_node(event)
            self._update_timeline(event)
            self._update_co_occurrences(event)
            self._check_anomaly(event.node_id)

    def _upsert_node(self, event: CanonicalEvent):
        nid = event.node_id
        now = event.timestamp

        if nid not in self.G:
            self.G.add_node(nid,
                layer              = event.layer,
                layer_name         = event.layer_name,
                event_type         = event.event_type,
                severity           = event.severity,
                observation_weight = 0.0,
                event_count        = 0,
                last_seen          = now,
                first_seen         = now,
                payload            = event.payload,
            )
        else:
            d = self.G.nodes[nid]
            d["event_count"]  += 1
            d["last_seen"]     = now
            d["severity"]      = event.severity
            d["payload"]       = event.payload
            # Increment observation weight on each event
            d["observation_weight"] += 1.0

    def _update_timeline(self, event: CanonicalEvent):
        self.timeline.append((event.timestamp, event.node_id))
        # Keep only last 10k entries
        if len(self.timeline) > 10_000:
            self.timeline = self.timeline[-10_000:]

    def _update_co_occurrences(self, event: CanonicalEvent):
        """
        Find all nodes that fired within CO_OCCURRENCE_WINDOW_SECONDS
        of this event and update W(u,v,t) on edges between them.
        """
        now     = event.timestamp
        nid     = event.node_id
        window  = self.CO_OCCURRENCE_WINDOW_SECONDS

        recent_nodes = [
            node_id for ts, node_id in self.timeline
            if node_id != nid
            and (now - ts).total_seconds() <= window
        ]

        for other_id in set(recent_nodes):
            if other_id not in self.G:
                continue

            t_self  = self.G.nodes[nid].get("last_seen", now)
            t_other = self.G.nodes[other_id].get("last_seen", now)
            delta   = abs((t_self - t_other).total_seconds())

            # W(u,v,t) = co_occurrence * e^(-λ * Δt)
            co_score = math.exp(-self.DECAY_LAMBDA * delta)

            # Add or update edge
            if self.G.has_edge(nid, other_id):
                e = self.G.edges[nid, other_id]
                e["co_occurrence_count"] += 1
                e["weight"]              += co_score
                e["last_co_occurrence"]   = now
            else:
                self.G.add_edge(nid, other_id,
                    co_occurrence_count = 1,
                    weight              = co_score,
                    last_co_occurrence  = now,
                )

    def _check_anomaly(self, node_id: str):
        node = self.G.nodes.get(node_id, {})
        w    = node.get("observation_weight", 0)
        if w >= self.ANOMALY_THRESHOLD:
            log.warning("anomaly_detected",
                node_id = node_id,
                weight  = round(w, 3),
                layer   = node.get("layer_name"),
                severity= node.get("severity"),
            )

    # ── Query ──────────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[dict]:
        if node_id not in self.G:
            return None
        return {"id": node_id, **self.G.nodes[node_id]}

    def get_all_nodes(self) -> list[dict]:
        return [{"id": nid, **data} for nid, data in self.G.nodes(data=True)]

    def get_all_edges(self) -> list[dict]:
        return [
            {"source": u, "target": v, **data}
            for u, v, data in self.G.edges(data=True)
        ]

    def get_neighbors(self, node_id: str) -> list[dict]:
        if node_id not in self.G:
            return []
        return [
            {"id": n, **self.G.nodes[n]}
            for n in nx.all_neighbors(self.G, node_id)
        ]

    def stats(self) -> dict:
        return {
            "nodes":    self.G.number_of_nodes(),
            "edges":    self.G.number_of_edges(),
            "timeline": len(self.timeline),
        }
