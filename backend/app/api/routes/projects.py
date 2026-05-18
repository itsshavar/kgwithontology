from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission, require_project_role
from app.db.session import get_db
from app.models.domain_profile import DomainProfile
from app.models.project import Project
from app.models.security import ProjectMembership, User
from app.schemas.project import ProjectCreate, ProjectMembershipCreate, ProjectMembershipRead, ProjectRead
from app.services.audit import record_audit
from app.services.graph.neo4j_service import neo4j_service

router = APIRouter(prefix="/projects", tags=["projects"])


def _safe_sync_project(project: Project) -> None:
    try:
        neo4j_service.sync_project(project)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j project sync warning: {exc}")


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(require_permission("projects:write")),
) -> Project:
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
    db.flush()
    if user:
        db.add(ProjectMembership(project_id=project.id, user_id=user.id, role="owner"))
        record_audit(db, "project.create", "project", project.id, actor=user, metadata={"name": project.name})
    db.commit()
    db.refresh(project)
    _safe_sync_project(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    db: Session = Depends(get_db),
    _: User | None = Depends(require_permission("projects:read")),
) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.id.desc())).all())


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: User | None = Depends(require_project_role("owner", "admin", "ontology_engineer", "data_analyst", "viewer", "api_user")),
) -> Project:
    return _get_project_or_404(project_id, db)


@router.post("/{project_id}/members", response_model=ProjectMembershipRead, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: int,
    payload: ProjectMembershipCreate,
    db: Session = Depends(get_db),
    actor: User | None = Depends(require_project_role("owner", "admin")),
) -> ProjectMembership:
    _get_project_or_404(project_id, db)
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found.")
    existing = db.scalar(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == payload.user_id,
        )
    )
    if existing:
        existing.role = payload.role
        membership = existing
    else:
        membership = ProjectMembership(project_id=project_id, user_id=payload.user_id, role=payload.role)
        db.add(membership)
    if actor:
        record_audit(
            db,
            "project.member.upsert",
            "project_membership",
            None,
            actor=actor,
            metadata={"project_id": project_id, "user_id": payload.user_id, "role": payload.role},
        )
    db.commit()
    db.refresh(membership)
    return membership


@router.get("/{project_id}/members", response_model=list[ProjectMembershipRead])
def list_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    _: User | None = Depends(require_project_role("owner", "admin", "ontology_engineer", "data_analyst", "viewer", "api_user")),
) -> list[ProjectMembership]:
    _get_project_or_404(project_id, db)
    return list(
        db.scalars(
            select(ProjectMembership).where(ProjectMembership.project_id == project_id).order_by(ProjectMembership.id.desc())
        ).all()
    )
