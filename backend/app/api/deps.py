from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token, hash_api_key
from app.db.session import get_db
from app.models.security import ApiKey, User

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
) -> User:
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
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superuser:
        role_names = {user_role.role.name for user_role in user.roles if user_role.role}
        if "Admin" not in role_names:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return user
