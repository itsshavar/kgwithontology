from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain_profile import DomainProfile
from app.models.project import Project
from app.models.source_document import SourceDocument
from app.schemas.document import DocumentRead, DocumentUrlIngest
from app.schemas.extraction import DocumentUploadResponse, KGExtractionRunResponse
from app.schemas.ontology import OntologyGenerateResponse
from app.services.extraction.document_kg_extractor import extract_kg_from_documents
from app.services.ingestion.document_service import save_bytes, save_upload
from app.services.ontology.generator import auto_generate_ontology

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _process_document(project: Project, document: SourceDocument, db: Session, auto_extract: bool) -> DocumentUploadResponse:
    extraction_summary: KGExtractionRunResponse | None = None
    ontology_summary: OntologyGenerateResponse | None = None
    if auto_extract and (document.raw_text or "").strip():
        extraction_result = extract_kg_from_documents(project=project, documents=[document], db=db)
        extraction_summary = KGExtractionRunResponse(**extraction_result)

        domain_profile = db.get(DomainProfile, project.domain_profile_id) if project.domain_profile_id else None
        ontology_summary = auto_generate_ontology(
            project=project,
            documents=[document],
            domain_profile=domain_profile,
            db=db,
        )

    return DocumentUploadResponse(
        document=DocumentRead.model_validate(document),
        extraction=extraction_summary,
        ontology=ontology_summary,
    )


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    auto_extract: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    project = _get_project_or_404(project_id, db)

    document = await save_upload(project_id, file)
    db.add(document)
    db.commit()
    db.refresh(document)
    return _process_document(project, document, db, auto_extract)


@router.post("/bulk", response_model=list[DocumentUploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents_bulk(
    project_id: int,
    files: list[UploadFile] = File(...),
    auto_extract: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[DocumentUploadResponse]:
    project = _get_project_or_404(project_id, db)
    responses: list[DocumentUploadResponse] = []
    for file in files:
        document = await save_upload(project_id, file)
        db.add(document)
        db.commit()
        db.refresh(document)
        responses.append(_process_document(project, document, db, auto_extract))
    return responses


@router.post("/zip", response_model=list[DocumentUploadResponse], status_code=status.HTTP_201_CREATED)
async def ingest_zip_archive(
    project_id: int,
    file: UploadFile = File(...),
    auto_extract: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> list[DocumentUploadResponse]:
    project = _get_project_or_404(project_id, db)
    file_bytes = await file.read()
    responses: list[DocumentUploadResponse] = []
    try:
        with ZipFile(BytesIO(file_bytes)) as archive:
            for member in archive.infolist():
                if member.is_dir() or member.file_size == 0:
                    continue
                filename = Path(member.filename).name
                if not filename:
                    continue
                document = save_bytes(project_id, filename, None, archive.read(member))
                db.add(document)
                db.commit()
                db.refresh(document)
                responses.append(_process_document(project, document, db, auto_extract))
    except BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid ZIP archive.") from exc
    return responses


@router.post("/url", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def ingest_remote_url(
    project_id: int,
    payload: DocumentUrlIngest,
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    project = _get_project_or_404(project_id, db)
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(payload.url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch remote URL: {exc}") from exc
    filename = payload.filename or Path(httpx.URL(payload.url).path).name or "remote_document"
    document = save_bytes(project_id, filename, response.headers.get("content-type"), response.content)
    db.add(document)
    db.commit()
    db.refresh(document)
    return _process_document(project, document, db, payload.auto_extract)


@router.get("", response_model=list[DocumentRead])
def list_project_documents(project_id: int, db: Session = Depends(get_db)) -> list[SourceDocument]:
    _get_project_or_404(project_id, db)

    query = select(SourceDocument).where(SourceDocument.project_id == project_id).order_by(SourceDocument.id.desc())
    return list(db.scalars(query).all())
