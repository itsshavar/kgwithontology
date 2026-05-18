from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str
    content_type: str | None = None
    chunk_count: int
    status: str
    created_at: datetime


class DocumentUrlIngest(BaseModel):
    url: str
    filename: str | None = None
    auto_extract: bool = True
