from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OntologyClassCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    label: str | None = None
    description: str | None = None
    parent_class_id: int | None = None
    status: str = "draft"
    source: str = "manual"
    confidence: float | None = None


class OntologyClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    label: str | None = None
    description: str | None = None
    parent_class_id: int | None = None
    status: str | None = None
    source: str | None = None
    confidence: float | None = None


class OntologyClassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    parent_class_id: int | None = None
    name: str
    label: str | None = None
    description: str | None = None
    status: str
    source: str
    confidence: float | None = None
    created_at: datetime


class OntologyPropertyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    label: str | None = None
    description: str | None = None
    property_type: str = Field(default="object", pattern="^(object|data)$")
    domain_class_id: int | None = None
    range_class_id: int | None = None
    range_datatype: str | None = None
    status: str = "draft"
    confidence: float | None = None


class OntologyPropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    label: str | None = None
    description: str | None = None
    property_type: str | None = Field(default=None, pattern="^(object|data)$")
    domain_class_id: int | None = None
    range_class_id: int | None = None
    range_datatype: str | None = None
    status: str | None = None
    confidence: float | None = None


class OntologyPropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    label: str | None = None
    description: str | None = None
    property_type: str
    domain_class_id: int | None = None
    range_class_id: int | None = None
    range_datatype: str | None = None
    status: str
    confidence: float | None = None
    created_at: datetime
