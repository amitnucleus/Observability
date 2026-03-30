import math
import threading
from datetime import datetime, timezone
from collections import defaultdict
from typing import Optional
import networkx as nx
import structlog

from consumer.schema import CanonicalEvent
from graph.types import EdgeType, MinimizationAction, NodeType, Scope
from graph.type_layer import (
    get_collapse_target,
    get_minimization_action,
    infer_edge_type,
    is_legal_connection,
)

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
        - node_type: Abstract Graph NodeType (e.g. NETWORK_REQUEST, DB_WRITER)
        - observation_weight: W(u,v,t) accumulated score
        - last_seen: timestamp of most recent event
        - event_count: total events seen on this node

    Edges carry:
        - edge_type: Abstract Graph EdgeType (e.g. TRIGGERS, CALLS, CO_OCCURS)
        - co_occurrence_count: how many times both nodes fired in the same window
        - weight: W(u,v,t) score on the edge
        - last_co_occurrence: timestamp
        - is_legal: whether the Type Layer permits this connection
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

        # Resolve the NodeType from the event
        try:
            node_type = NodeType(event.node_type)
        except ValueError:
            node_type = NodeType.UNKNOWN

        if nid not in self.G:
            self.G.add_node(nid,
                layer              = event.layer,
                layer_name         = event.layer_name,
                event_type         = event.event_type,
                severity           = event.severity,
                node_type          = node_type.value,
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
            d["node_type"]     = node_type.value
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

            # Infer edge type from source/target NodeTypes
            src_type_str = self.G.nodes[nid].get("node_type", "UNKNOWN")
            tgt_type_str = self.G.nodes[other_id].get("node_type", "UNKNOWN")
            try:
                src_type = NodeType(src_type_str)
                tgt_type = NodeType(tgt_type_str)
            except ValueError:
                src_type = NodeType.UNKNOWN
                tgt_type = NodeType.UNKNOWN

            edge_type = infer_edge_type(src_type, tgt_type)
            legal     = is_legal_connection(src_type, tgt_type)

            if not legal:
                log.debug("type_layer_violation",
                    source=nid, target=other_id,
                    source_type=src_type_str, target_type=tgt_type_str,
                )

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
                    edge_type           = edge_type.value,
                    is_legal            = legal,
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

    # ── Scope-filtered views (Minimization Operators) ────────

    def get_scoped_nodes(self, scope: Scope) -> list[dict]:
        """
        Return nodes after applying minimization operators for the given scope.

        KEEP     → node appears as-is
        COLLAPSE → node is replaced by its collapsed parent type
        EXCLUDE  → node is removed from the view
        """
        collapsed: dict[str, dict] = {}   # collapsed_id → merged data
        kept:      list[dict]      = []

        for nid, data in self.G.nodes(data=True):
            try:
                nt = NodeType(data.get("node_type", "UNKNOWN"))
            except ValueError:
                nt = NodeType.UNKNOWN

            action = get_minimization_action(nt, scope)

            if action == MinimizationAction.EXCLUDE:
                continue

            if action == MinimizationAction.COLLAPSE:
                parent_type = get_collapse_target(nt)
                parent_id   = f"{parent_type.value}:{data.get('layer_name', 'unknown')}"

                if parent_id not in collapsed:
                    collapsed[parent_id] = {
                        "id":                 parent_id,
                        "layer":              data.get("layer", 0),
                        "layer_name":         data.get("layer_name", ""),
                        "event_type":         "collapsed",
                        "severity":           data.get("severity", "INFO"),
                        "node_type":          parent_type.value,
                        "observation_weight": data.get("observation_weight", 0),
                        "event_count":        data.get("event_count", 0),
                        "collapsed_count":    1,
                        "collapsed_from":     [nid],
                    }
                else:
                    p = collapsed[parent_id]
                    p["observation_weight"] += data.get("observation_weight", 0)
                    p["event_count"]        += data.get("event_count", 0)
                    p["collapsed_count"]    += 1
                    p["collapsed_from"].append(nid)
                    # Keep the worst severity
                    if data.get("severity") == "ERROR":
                        p["severity"] = "ERROR"
                    elif data.get("severity") == "WARN" and p["severity"] != "ERROR":
                        p["severity"] = "WARN"

            else:  # KEEP
                kept.append({"id": nid, **data})

        return kept + list(collapsed.values())

    def get_scoped_edges(self, scope: Scope) -> list[dict]:
        """
        Return edges after applying scope filtering.

        Edges connected to excluded nodes are removed.
        Edges connected to collapsed nodes are re-routed to the parent.
        """
        # Build the node mapping: original_id → scoped_id (or None if excluded)
        node_map: dict[str, Optional[str]] = {}

        for nid, data in self.G.nodes(data=True):
            try:
                nt = NodeType(data.get("node_type", "UNKNOWN"))
            except ValueError:
                nt = NodeType.UNKNOWN

            action = get_minimization_action(nt, scope)

            if action == MinimizationAction.EXCLUDE:
                node_map[nid] = None
            elif action == MinimizationAction.COLLAPSE:
                parent_type = get_collapse_target(nt)
                node_map[nid] = f"{parent_type.value}:{data.get('layer_name', 'unknown')}"
            else:
                node_map[nid] = nid

        # Re-map edges
        merged_edges: dict[tuple[str, str], dict] = {}

        for u, v, data in self.G.edges(data=True):
            mapped_u = node_map.get(u)
            mapped_v = node_map.get(v)

            # Skip edges to/from excluded nodes
            if mapped_u is None or mapped_v is None:
                continue
            # Skip self-loops created by collapsing
            if mapped_u == mapped_v:
                continue

            key = (mapped_u, mapped_v)
            if key in merged_edges:
                e = merged_edges[key]
                e["co_occurrence_count"] += data.get("co_occurrence_count", 0)
                e["weight"]             += data.get("weight", 0)
            else:
                merged_edges[key] = {
                    "source":              mapped_u,
                    "target":              mapped_v,
                    "co_occurrence_count": data.get("co_occurrence_count", 0),
                    "weight":              data.get("weight", 0),
                    "edge_type":           data.get("edge_type", "CO_OCCURS"),
                    "is_legal":            data.get("is_legal", True),
                }

        return list(merged_edges.values())

    def detect_anomalies(self, threshold: Optional[float] = None) -> list[dict]:
        """Return nodes whose observation_weight exceeds the threshold."""
        t = threshold if threshold is not None else self.ANOMALY_THRESHOLD
        anomalies = []
        for nid, data in self.G.nodes(data=True):
            w = data.get("observation_weight", 0)
            if w >= t:
                anomalies.append({
                    "node_id":    nid,
                    "layer":      data.get("layer", 0),
                    "layer_name": data.get("layer_name", ""),
                    "node_type":  data.get("node_type", "UNKNOWN"),
                    "severity":   data.get("severity", "INFO"),
                    "weight":     round(w, 3),
                    "event_count": data.get("event_count", 0),
                })
        anomalies.sort(key=lambda x: x["weight"], reverse=True)
        return anomalies
