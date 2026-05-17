import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.operations import ExtractionJob
from app.models.project import Project
from app.models.source_document import SourceDocument
from app.schemas.extraction import KGExtractionRunResponse
from app.schemas.operations import ExtractionJobCreate, ExtractionJobRead
from app.services.extraction.document_kg_extractor import extract_kg_from_documents
from app.tasks.extraction_tasks import run_project_extraction_job

router = APIRouter(prefix="/projects/{project_id}/jobs", tags=["jobs"])


@router.post("/extraction", response_model=ExtractionJobRead, status_code=status.HTTP_201_CREATED)
def create_extraction_job(project_id: int, payload: ExtractionJobCreate, db: Session = Depends(get_db)) -> ExtractionJob:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    documents = []
    if payload.document_id is not None:
        document = db.get(SourceDocument, payload.document_id)
        if not document or document.project_id != project_id:
            raise HTTPException(status_code=404, detail="Document not found.")
        documents = [document]
    job = ExtractionJob(project_id=project_id, document_id=payload.document_id, mode=payload.mode, status="queued")
    db.add(job)
    db.flush()
    if payload.run_inline:
        try:
            selected_documents = documents or list(db.scalars(select(SourceDocument).where(SourceDocument.project_id == project_id)).all())
            result = extract_kg_from_documents(project=project, documents=selected_documents, db=db)
            KGExtractionRunResponse(**result)
            job.status = "completed"
            job.progress = 1.0
            job.result_json = json.dumps(result, sort_keys=True)
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
    else:
        db.flush()
        run_project_extraction_job.delay(job.id)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[ExtractionJobRead])
def list_jobs(project_id: int, db: Session = Depends(get_db)) -> list[ExtractionJob]:
    return list(db.scalars(select(ExtractionJob).where(ExtractionJob.project_id == project_id).order_by(ExtractionJob.id.desc())).all())
