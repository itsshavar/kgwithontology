from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.services.export_service import serialize_project_graph

router = APIRouter(prefix="/projects/{project_id}/export", tags=["export"])


@router.get("/rdf")
def export_project_rdf(project_id: int, db: Session = Depends(get_db)) -> Response:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    payload, media_type, extension = serialize_project_graph(project, db, "rdf")
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="project_{project_id}.{extension}"'},
    )


@router.get("/owl")
def export_project_owl(project_id: int, db: Session = Depends(get_db)) -> Response:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    payload, media_type, extension = serialize_project_graph(project, db, "owl")
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="project_{project_id}.{extension}"'},
    )


@router.get("/jsonld")
def export_project_jsonld(project_id: int, db: Session = Depends(get_db)) -> Response:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    payload, media_type, extension = serialize_project_graph(project, db, "json-ld")
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="project_{project_id}.{extension}"'},
    )


@router.get("/turtle")
def export_project_turtle(project_id: int, db: Session = Depends(get_db)) -> Response:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    payload, media_type, extension = serialize_project_graph(project, db, "turtle")
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="project_{project_id}.{extension}"'},
    )
