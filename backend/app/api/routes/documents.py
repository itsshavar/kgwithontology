from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.project import Project
from app.models.source_document import SourceDocument
from app.schemas.document import DocumentRead
from app.schemas.extraction import DocumentUploadResponse, KGExtractionRunResponse
from app.services.extraction.document_kg_extractor import extract_kg_from_documents
from app.services.ingestion.document_service import save_upload
from app.services.ontology.generator import auto_generate_ontology

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
    auto_extract: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    document = await save_upload(project_id, file)
    db.add(document)
    db.commit()
    db.refresh(document)

    extraction_summary: KGExtractionRunResponse | None = None
    ontology_summary: OntologyGenerateResponse | None = None
    if auto_extract and (document.raw_text or "").strip():
        extraction_result = extract_kg_from_documents(project=project, documents=[document], db=db)
        extraction_summary = KGExtractionRunResponse(**extraction_result)

        # Auto-generate ontology
        domain_profile = db.get(DomainProfile, project.domain_profile_id) if project.domain_profile_id else None
        ontology_summary = auto_generate_ontology(
            project=project,
            documents=[document],
            domain_profile=domain_profile,
            db=db,
        )

    return DocumentUploadResponse(document=DocumentRead.model_validate(document), extraction=extraction_summary, ontology=ontology_summary)


@router.get("", response_model=list[DocumentRead])
def list_project_documents(project_id: int, db: Session = Depends(get_db)) -> list[SourceDocument]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    query = select(SourceDocument).where(SourceDocument.project_id == project_id).order_by(SourceDocument.id.desc())
    return list(db.scalars(query).all())
