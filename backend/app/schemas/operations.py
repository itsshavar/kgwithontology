from datetime import datetime

from pydantic import BaseModel, Field


class ExtractionJobCreate(BaseModel):
    document_id: int | None = None
    mode: str = Field(default="hybrid", pattern="^(rule_based|ml|llm|hybrid)$")
    run_inline: bool = True


class ExtractionJobRead(BaseModel):
    id: int
    project_id: int
    document_id: int | None = None
    mode: str
    status: str
    progress: float
    result_json: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class QueryRequest(BaseModel):
    language: str = Field(default="cypher", pattern="^(cypher|sparql|full_text|semantic)$")
    query: str
    limit: int = Field(default=100, ge=1, le=1000)


class QueryResponse(BaseModel):
    language: str
    executed: bool
    rows: list[dict]
    message: str


class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=100)


class SearchHit(BaseModel):
    type: str
    id: int
    label: str
    snippet: str | None = None
    score: float = 1.0


class SearchResponse(BaseModel):
    hits: list[SearchHit]


class VisualizationResponse(BaseModel):
    nodes: list[dict]
    edges: list[dict]
    ontology_tree: list[dict]
    timeline: list[dict]
