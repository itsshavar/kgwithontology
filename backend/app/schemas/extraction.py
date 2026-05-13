from pydantic import BaseModel, Field

from app.schemas.document import DocumentRead
from app.schemas.ontology import OntologyGenerateResponse


class KGExtractionRunResponse(BaseModel):
    project_id: int
    processed_documents: int = 0
    document_ids: list[int] = Field(default_factory=list)
    created_entities: int = 0
    reused_entities: int = 0
    typed_entities: int = 0
    created_relations: int = 0
    created_properties: int = 0
    message: str


class DocumentUploadResponse(BaseModel):
    document: DocumentRead
    extraction: KGExtractionRunResponse | None = None
    ontology: OntologyGenerateResponse | None = None
