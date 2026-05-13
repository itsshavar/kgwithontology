import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain_profile import DomainProfile
from app.schemas.domain_profile import DomainProfileCreate, DomainProfileRead

router = APIRouter(prefix="/domain-profiles", tags=["domain-profiles"])


@router.post("", response_model=DomainProfileRead, status_code=status.HTTP_201_CREATED)
def create_domain_profile(payload: DomainProfileCreate, db: Session = Depends(get_db)) -> DomainProfile:
    existing = db.scalar(select(DomainProfile).where(DomainProfile.name == payload.name))
    if existing:
        raise HTTPException(status_code=409, detail="Domain profile with this name already exists.")

    domain_profile = DomainProfile(
        name=payload.name,
        description=payload.description,
        seed_schema=json.dumps({"seed_classes": payload.seed_classes}),
        relation_types=json.dumps(payload.relation_types),
        synonyms=json.dumps(payload.synonyms),
    )
    db.add(domain_profile)
    db.commit()
    db.refresh(domain_profile)
    return domain_profile


@router.get("", response_model=list[DomainProfileRead])
def list_domain_profiles(db: Session = Depends(get_db)) -> list[DomainProfile]:
    return list(db.scalars(select(DomainProfile).order_by(DomainProfile.id.desc())).all())
