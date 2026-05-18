from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8)
    full_name: str | None = None


class UserRead(BaseModel):
    id: int
    email: EmailStr
    username: str
    full_name: str | None = None
    is_active: bool
    is_superuser: bool
    mfa_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class RoleRead(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    api_key: str


class AuditLogRead(BaseModel):
    id: int
    actor_user_id: int | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    metadata_json: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
