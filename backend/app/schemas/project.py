from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    domain_profile_id: int | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    domain_profile_id: int | None = None
    created_at: datetime


class ProjectMembershipCreate(BaseModel):
    user_id: int
    role: str = Field(default="viewer", pattern="^(owner|admin|ontology_engineer|data_analyst|viewer|api_user)$")


class ProjectMembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role: str
    created_at: datetime
