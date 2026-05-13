from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DomainProfileCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    seed_classes: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)
    synonyms: dict[str, list[str]] = Field(default_factory=dict)


class DomainProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime
