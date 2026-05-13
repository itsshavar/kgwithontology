from pydantic import BaseModel, Field


class OntologyGenerateRequest(BaseModel):
    max_candidates: int = Field(default=15, ge=1, le=100)
    min_term_length: int = Field(default=4, ge=2, le=30)


class OntologyCandidate(BaseModel):
    term: str
    frequency: int
    suggested_type: str
    evidence: str | None = None


class OntologyGenerateResponse(BaseModel):
    project_id: int
    total_documents: int
    total_chunks: int
    candidates: list[OntologyCandidate]
