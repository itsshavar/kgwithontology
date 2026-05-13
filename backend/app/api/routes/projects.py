from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain_profile import DomainProfile
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead
from app.services.graph.neo4j_service import neo4j_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _safe_sync_project(project: Project) -> None:
    try:
        neo4j_service.sync_project(project)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j project sync warning: {exc}")


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    if payload.domain_profile_id is not None:
        domain_profile = db.get(DomainProfile, payload.domain_profile_id)
        if not domain_profile:
            raise HTTPException(status_code=404, detail="Domain profile not found.")

    project = Project(
        name=payload.name,
        description=payload.description,
        domain_profile_id=payload.domain_profile_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    _safe_sync_project(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.id.desc())).all())


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project
