from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, generate_api_key, hash_secret, verify_secret
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.security import ApiKey, Role, User, UserRole
from app.schemas.security import ApiKeyCreate, ApiKeyResponse, LoginRequest, TokenResponse, UserCreate, UserRead
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(or_(User.email == payload.email, User.username == payload.username)))
    if existing:
        raise HTTPException(status_code=409, detail="User with this email or username already exists.")
    is_first_user = db.scalar(select(User.id).limit(1)) is None
    user = User(
        email=str(payload.email),
        username=payload.username,
        full_name=payload.full_name,
        hashed_password=hash_secret(payload.password),
        is_superuser=is_first_user,
    )
    db.add(user)
    db.flush()
    role = db.scalar(select(Role).where(Role.name == ("Admin" if is_first_user else "Viewer")))
    if role:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    record_audit(db, "user.register", "user", user.id, metadata={"first_user": is_first_user})
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(or_(User.username == payload.username, User.email == payload.username)))
    if not user or not verify_secret(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled.")
    role_names = [user_role.role.name for user_role in user.roles if user_role.role]
    token = create_access_token(str(user.id), {"roles": role_names})
    record_audit(db, "user.login", "user", user.id, actor=user)
    db.commit()
    return TokenResponse(access_token=token, expires_in=settings.access_token_minutes * 60, user=UserRead.model_validate(user))


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(payload: ApiKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ApiKeyResponse:
    raw, key_hash = generate_api_key()
    record = ApiKey(user_id=user.id, name=payload.name, key_hash=key_hash, prefix=raw[:8])
    db.add(record)
    record_audit(db, "api_key.create", "api_key", None, actor=user, metadata={"name": payload.name})
    db.commit()
    db.refresh(record)
    return ApiKeyResponse(id=record.id, name=record.name, prefix=record.prefix, api_key=raw)
