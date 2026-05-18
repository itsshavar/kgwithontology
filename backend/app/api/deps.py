from collections.abc import Callable

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token, hash_api_key
from app.db.session import get_db
from app.models.security import ApiKey, ProjectMembership, User

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None,
    api_key: str | None,
    db: Session,
) -> User | None:
    if api_key:
        key_hash = hash_api_key(api_key)
        record = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True)))
        if record:
            user = db.get(User, record.user_id)
            if user and user.is_active:
                return user
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            user_id = int(payload["sub"])
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.") from exc
        user = db.get(User, user_id)
        if user and user.is_active:
            return user
    return None


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> User | None:
    return _user_from_credentials(credentials, api_key, db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> User:
    user = _user_from_credentials(credentials, api_key, db)
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")


def _role_names(user: User) -> set[str]:
    return {user_role.role.name for user_role in user.roles if user_role.role}


def user_has_permission(user: User, permission_code: str) -> bool:
    if user.is_superuser or "Admin" in _role_names(user):
        return True
    for user_role in user.roles:
        role = user_role.role
        if not role:
            continue
        for role_permission in role.permissions:
            permission = role_permission.permission
            if permission and permission.code in {"*", permission_code}:
                return True
    return False


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user_has_permission(user, "*"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return user


def require_permission(permission_code: str) -> Callable[..., User | None]:
    def dependency(
        credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
        api_key: str | None = Security(api_key_header),
        db: Session = Depends(get_db),
    ) -> User | None:
        user = _user_from_credentials(credentials, api_key, db)
        if not settings.require_auth:
            return user
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        if not user_has_permission(user, permission_code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission '{permission_code}' required.")
        return user

    return dependency


def require_project_role(*allowed_roles: str) -> Callable[..., User | None]:
    def dependency(
        project_id: int,
        credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
        api_key: str | None = Security(api_key_header),
        db: Session = Depends(get_db),
    ) -> User | None:
        user = _user_from_credentials(credentials, api_key, db)
        if not settings.require_auth:
            return user
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        if user_has_permission(user, "*"):
            return user
        membership = db.scalar(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user.id,
            )
        )
        if membership and membership.role in allowed_roles:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project role is not sufficient.")

    return dependency
