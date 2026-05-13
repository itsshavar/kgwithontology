from datetime import datetime

from pydantic import BaseModel, Field


class EntityCreate(BaseModel):
    canonical_name: str = Field(..., min_length=2, max_length=255)
    ontology_class_id: int | None = None
    aliases: list[str] = Field(default_factory=list)
    confidence: float | None = None
    source: str = "manual"


class EntityRead(BaseModel):
    id: int
    project_id: int
    ontology_class_id: int | None = None
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    confidence: float | None = None
    source: str
    created_at: datetime


class RelationInstanceCreate(BaseModel):
    subject_entity_id: int
    predicate_id: int
    object_entity_id: int | None = None
    object_value: str | None = None
    evidence_text: str | None = None
    source_document_id: int | None = None
    confidence: float | None = None


class RelationInstanceUpdate(BaseModel):
    subject_entity_id: int | None = None
    predicate_id: int | None = None
    object_entity_id: int | None = None
    object_value: str | None = None
    evidence_text: str | None = None
    source_document_id: int | None = None
    confidence: float | None = None


class RelationInstanceRead(BaseModel):
    id: int
    project_id: int
    subject_entity_id: int
    predicate_id: int
    object_entity_id: int | None = None
    object_value: str | None = None
    evidence_text: str | None = None
    source_document_id: int | None = None
    confidence: float | None = None
    created_at: datetime


class RelationEvidenceRead(BaseModel):
    relation_id: int
    source_document_id: int | None = None
    source_filename: str | None = None
    evidence_text: str | None = None
    before: str = ""
    highlight: str = ""
    after: str = ""
    start_offset: int | None = None
    end_offset: int | None = None
