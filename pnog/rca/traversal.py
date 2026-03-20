import networkx as nx
from graph.engine import get_graph
import structlog

log = structlog.get_logger()

def trace(node_id: str, max_depth: int = 6) -> dict:
    """
    Given a fault node, traverse the PNOG graph to find root cause candidates.
    Returns ranked list of candidate nodes with their blast radius.
    """
    g = get_graph()

    if node_id not in g.G:
        return {"error": f"Node {node_id} not found in graph"}

    # BFS traversal from fault node
    visited    = {}
    queue      = [(node_id, 0, 1.0)]  # (node, depth, accumulated_weight)
    candidates = []

    while queue:
        current, depth, acc_weight = queue.pop(0)
        if current in visited or depth > max_depth:
            continue
        visited[current] = acc_weight

        node_data = g.G.nodes[current]
        candidates.append({
            "node_id":    current,
            "layer":      node_data.get("layer"),
            "layer_name": node_data.get("layer_name"),
            "severity":   node_data.get("severity"),
            "weight":     round(node_data.get("observation_weight", 0), 3),
            "path_weight": round(acc_weight, 3),
            "event_count": node_data.get("event_count", 0),
            "depth":      depth,
        })

        # Traverse neighbors weighted by edge weight
        for neighbor in g.G.neighbors(current):
            if neighbor not in visited:
                edge_w = g.G.edges[current, neighbor].get("weight", 0)
                queue.append((neighbor, depth + 1, acc_weight * edge_w))

    # Rank by combination of observation weight and path weight
    candidates.sort(key=lambda x: x["weight"] * x["path_weight"], reverse=True)

    # Blast radius — all nodes reachable from fault node
    try:
        blast_radius = list(nx.descendants(g.G, node_id))
    except Exception:
        blast_radius = []

    log.info("rca_trace_complete",
        fault_node    = node_id,
        candidates    = len(candidates),
        blast_radius  = len(blast_radius),
    )

    return {
        "fault_node":   node_id,
        "candidates":   candidates[:10],  # top 10
        "blast_radius": blast_radius,
        "graph_stats":  g.stats(),
    }


def get_anomalies(threshold: float = 5.0) -> list[dict]:
    """Return all nodes currently above the anomaly threshold."""
    g = get_graph()
    anomalies = []
    for nid, data in g.G.nodes(data=True):
        w = data.get("observation_weight", 0)
        if w >= threshold:
            anomalies.append({
                "node_id":    nid,
                "layer_name": data.get("layer_name"),
                "weight":     round(w, 3),
                "severity":   data.get("severity"),
                "event_count": data.get("event_count", 0),
            })
    anomalies.sort(key=lambda x: x["weight"], reverse=True)
    return anomalies
