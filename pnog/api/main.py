import strawberry
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from typing import Optional
from graph.engine import get_graph
from rca.traversal import trace, get_anomalies

# ── GraphQL types ──────────────────────────────────────────────

@strawberry.type
class GraphNode:
    id:          str
    layer:       int
    layer_name:  str
    event_type:  str
    severity:    str
    weight:      float
    event_count: int

@strawberry.type
class GraphEdge:
    source:              str
    target:              str
    co_occurrence_count: int
    weight:              float

@strawberry.type
class RCACandidate:
    node_id:     str
    layer:       int
    layer_name:  str
    severity:    str
    weight:      float
    path_weight: float
    event_count: int
    depth:       int

@strawberry.type
class RCAResult:
    fault_node:   str
    candidates:   list[RCACandidate]
    blast_radius: list[str]

@strawberry.type
class GraphStats:
    nodes:    int
    edges:    int
    timeline: int

# ── Queries ────────────────────────────────────────────────────

@strawberry.type
class Query:

    @strawberry.field
    def nodes(self) -> list[GraphNode]:
        g = get_graph()
        return [
            GraphNode(
                id          = d["id"],
                layer       = d.get("layer", 0),
                layer_name  = d.get("layer_name", ""),
                event_type  = d.get("event_type", ""),
                severity    = d.get("severity", "INFO"),
                weight      = round(d.get("observation_weight", 0), 3),
                event_count = d.get("event_count", 0),
            )
            for d in g.get_all_nodes()
        ]

    @strawberry.field
    def edges(self) -> list[GraphEdge]:
        g = get_graph()
        return [
            GraphEdge(
                source              = e["source"],
                target              = e["target"],
                co_occurrence_count = e.get("co_occurrence_count", 0),
                weight              = round(e.get("weight", 0), 3),
            )
            for e in g.get_all_edges()
        ]

    @strawberry.field
    def rca(self, node_id: str, max_depth: Optional[int] = 6) -> RCAResult:
        result = trace(node_id, max_depth or 6)
        return RCAResult(
            fault_node   = result["fault_node"],
            blast_radius = result["blast_radius"],
            candidates   = [RCACandidate(**c) for c in result["candidates"]],
        )

    @strawberry.field
    def anomalies(self, threshold: Optional[float] = 5.0) -> list[GraphNode]:
        items = get_anomalies(threshold or 5.0)
        g = get_graph()
        result = []
        for a in items:
            nid  = a["node_id"]
            data = g.G.nodes.get(nid, {})
            result.append(GraphNode(
                id          = nid,
                layer       = data.get("layer", 0),
                layer_name  = a["layer_name"],
                event_type  = data.get("event_type", ""),
                severity    = a["severity"],
                weight      = a["weight"],
                event_count = a["event_count"],
            ))
        return result

    @strawberry.field
    def stats(self) -> GraphStats:
        s = get_graph().stats()
        return GraphStats(**s)


# ── App ────────────────────────────────────────────────────────

schema = strawberry.Schema(query=Query)

app = FastAPI(title="PNOG API")
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
def health():
    return {"status": "ok", **get_graph().stats()}
