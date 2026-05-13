from pydantic import BaseModel


class GraphHealthResponse(BaseModel):
    enabled: bool
    connected: bool
    uri: str | None = None
    database: str
    message: str


class GraphSyncResponse(BaseModel):
    project_id: int
    graph_enabled: bool
    synced: bool
    ontology_classes: int
    ontology_properties: int
    entities: int
    relation_instances: int
    message: str
