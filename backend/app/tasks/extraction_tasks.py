import json

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.operations import ExtractionJob
from app.models.project import Project
from app.models.source_document import SourceDocument
from app.services.extraction.document_kg_extractor import extract_kg_from_documents
from app.tasks.celery_app import celery_app


@celery_app.task(name="extraction.run_project_job")
def run_project_extraction_job(job_id: int) -> dict:
    with SessionLocal() as db:
        job = db.get(ExtractionJob, job_id)
        if not job:
            return {"status": "missing", "job_id": job_id}
        project = db.get(Project, job.project_id)
        if not project:
            job.status = "failed"
            job.error = "Project not found."
            db.commit()
            return {"status": "failed", "job_id": job_id}
        job.status = "running"
        job.progress = 0.1
        db.commit()
        documents = list(db.scalars(select(SourceDocument).where(SourceDocument.project_id == job.project_id)).all())
        if job.document_id:
            documents = [document for document in documents if document.id == job.document_id]
        try:
            result = extract_kg_from_documents(project=project, documents=documents, db=db)
            job.status = "completed"
            job.progress = 1.0
            job.result_json = json.dumps(result, sort_keys=True)
            db.commit()
            return result
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            db.commit()
            raise
