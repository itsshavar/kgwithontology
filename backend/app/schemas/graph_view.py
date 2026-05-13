from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    edge_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphViewResponse(BaseModel):
    project_id: int
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    ontology_class_count: int
    ontology_property_count: int
    entity_count: int
    relation_count: int
