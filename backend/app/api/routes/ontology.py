import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain_profile import DomainProfile
from app.models.ontology_class import OntologyClass
from app.models.ontology_property import OntologyProperty
from app.models.project import Project
from app.models.source_document import SourceDocument
from app.schemas.ontology import OntologyGenerateRequest, OntologyGenerateResponse
from app.schemas.ontology_import import OntologyImportResponse
from app.schemas.ontology_persistence import (
    OntologyClassCreate,
    OntologyClassRead,
    OntologyClassUpdate,
    OntologyPropertyCreate,
    OntologyPropertyRead,
    OntologyPropertyUpdate,
)
from app.services.graph.neo4j_service import neo4j_service
from app.services.ontology.generator import generate_candidates
from app.services.ontology.importer import OntologyImportError, import_ontology_payload
from app.services.ontology.rdf_importer import parse_rdf_ontology_bytes

router = APIRouter(prefix="/projects/{project_id}/ontology", tags=["ontology"])


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


def _get_project_class_or_404(project_id: int, class_id: int, db: Session) -> OntologyClass:
    ontology_class = db.get(OntologyClass, class_id)
    if not ontology_class or ontology_class.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ontology class not found in this project.")
    return ontology_class


def _get_project_property_or_404(project_id: int, property_id: int, db: Session) -> OntologyProperty:
    ontology_property = db.get(OntologyProperty, property_id)
    if not ontology_property or ontology_property.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ontology property not found in this project.")
    return ontology_property


def _safe_sync_ontology_class(project: Project, ontology_class: OntologyClass) -> None:
    try:
        neo4j_service.sync_ontology_class(project, ontology_class)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j ontology class sync warning: {exc}")


def _safe_sync_ontology_property(project: Project, ontology_property: OntologyProperty) -> None:
    try:
        neo4j_service.sync_ontology_property(project, ontology_property)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j ontology property sync warning: {exc}")


@router.post("/generate", response_model=OntologyGenerateResponse)
def generate_project_ontology(
    project_id: int,
    payload: OntologyGenerateRequest,
    db: Session = Depends(get_db),
) -> OntologyGenerateResponse:
    project = _get_project_or_404(project_id, db)

    documents = list(
        db.scalars(select(SourceDocument).where(SourceDocument.project_id == project_id)).all()
    )
    if not documents:
        raise HTTPException(status_code=400, detail="No documents uploaded for this project.")

    domain_profile = db.get(DomainProfile, project.domain_profile_id) if project.domain_profile_id else None

    return generate_candidates(
        project_id=project_id,
        documents=documents,
        domain_profile=domain_profile,
        max_candidates=payload.max_candidates,
        min_term_length=payload.min_term_length,
    )


@router.post("/import", response_model=OntologyImportResponse, status_code=status.HTTP_201_CREATED)
async def import_project_ontology(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> OntologyImportResponse:
    project = _get_project_or_404(project_id, db)

    try:
        payload_bytes = await file.read()
        filename = file.filename or "ontology"
        if filename.lower().endswith(".json") or (file.content_type or "").lower() in {"application/json", "text/json"}:
            payload = json.loads(payload_bytes.decode("utf-8"))
            if not isinstance(payload, dict):
                raise OntologyImportError("Ontology import payload must be a JSON object.")
            result = import_ontology_payload(project_id, payload, db)
            import_format = "json"
        else:
            rdf_payload, import_format = parse_rdf_ontology_bytes(
                payload_bytes,
                filename=file.filename,
                content_type=file.content_type,
            )
            result = import_ontology_payload(project_id, rdf_payload, db)
    except json.JSONDecodeError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid ontology JSON: {exc}") from exc
    except OntologyImportError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for ontology_class in result["created_classes"]:
        _safe_sync_ontology_class(project, ontology_class)  # type: ignore[arg-type]
    for ontology_class in result["updated_classes"]:
        _safe_sync_ontology_class(project, ontology_class)  # type: ignore[arg-type]
    for ontology_property in result["created_properties"]:
        _safe_sync_ontology_property(project, ontology_property)  # type: ignore[arg-type]
    for ontology_property in result["updated_properties"]:
        _safe_sync_ontology_property(project, ontology_property)  # type: ignore[arg-type]

    return OntologyImportResponse(
        project_id=project_id,
        imported_classes=len(result["created_classes"]),
        updated_classes=len(result["updated_classes"]),
        imported_properties=len(result["created_properties"]),
        updated_properties=len(result["updated_properties"]),
        message=f"Ontology import completed successfully from {import_format}.",
    )


@router.post("/classes", response_model=OntologyClassRead, status_code=status.HTTP_201_CREATED)
def create_ontology_class(
    project_id: int,
    payload: OntologyClassCreate,
    db: Session = Depends(get_db),
) -> OntologyClass:
    project = _get_project_or_404(project_id, db)

    existing = db.scalar(
        select(OntologyClass).where(
            OntologyClass.project_id == project_id,
            OntologyClass.name == payload.name,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Ontology class with this name already exists.")

    if payload.parent_class_id is not None:
        _get_project_class_or_404(project_id, payload.parent_class_id, db)

    ontology_class = OntologyClass(
        project_id=project_id,
        parent_class_id=payload.parent_class_id,
        name=payload.name,
        label=payload.label,
        description=payload.description,
        status=payload.status,
        source=payload.source,
        confidence=payload.confidence,
    )
    db.add(ontology_class)
    db.commit()
    db.refresh(ontology_class)
    _safe_sync_ontology_class(project, ontology_class)
    return ontology_class


@router.get("/classes", response_model=list[OntologyClassRead])
def list_ontology_classes(project_id: int, db: Session = Depends(get_db)) -> list[OntologyClass]:
    _get_project_or_404(project_id, db)
    query = select(OntologyClass).where(OntologyClass.project_id == project_id).order_by(OntologyClass.id.desc())
    return list(db.scalars(query).all())


@router.patch("/classes/{class_id}", response_model=OntologyClassRead)
def update_ontology_class(
    project_id: int,
    class_id: int,
    payload: OntologyClassUpdate,
    db: Session = Depends(get_db),
) -> OntologyClass:
    project = _get_project_or_404(project_id, db)
    ontology_class = _get_project_class_or_404(project_id, class_id, db)

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] and updates["name"] != ontology_class.name:
        existing = db.scalar(
            select(OntologyClass).where(
                OntologyClass.project_id == project_id,
                OntologyClass.name == updates["name"],
                OntologyClass.id != class_id,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Another ontology class with this name already exists.")

    if "parent_class_id" in updates:
        parent_class_id = updates["parent_class_id"]
        if parent_class_id == class_id:
            raise HTTPException(status_code=400, detail="A class cannot be its own parent.")
        if parent_class_id is not None:
            _get_project_class_or_404(project_id, parent_class_id, db)

    for field, value in updates.items():
        setattr(ontology_class, field, value)

    db.commit()
    db.refresh(ontology_class)
    _safe_sync_ontology_class(project, ontology_class)
    return ontology_class


@router.post("/properties", response_model=OntologyPropertyRead, status_code=status.HTTP_201_CREATED)
def create_ontology_property(
    project_id: int,
    payload: OntologyPropertyCreate,
    db: Session = Depends(get_db),
) -> OntologyProperty:
    project = _get_project_or_404(project_id, db)

    existing = db.scalar(
        select(OntologyProperty).where(
            OntologyProperty.project_id == project_id,
            OntologyProperty.name == payload.name,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Ontology property with this name already exists.")

    if payload.domain_class_id is not None:
        _get_project_class_or_404(project_id, payload.domain_class_id, db)
    if payload.range_class_id is not None:
        _get_project_class_or_404(project_id, payload.range_class_id, db)
    if payload.property_type == "data" and not payload.range_datatype:
        raise HTTPException(status_code=400, detail="Data properties should include range_datatype.")

    ontology_property = OntologyProperty(
        project_id=project_id,
        name=payload.name,
        label=payload.label,
        description=payload.description,
        property_type=payload.property_type,
        domain_class_id=payload.domain_class_id,
        range_class_id=payload.range_class_id,
        range_datatype=payload.range_datatype,
        status=payload.status,
        confidence=payload.confidence,
    )
    db.add(ontology_property)
    db.commit()
    db.refresh(ontology_property)
    _safe_sync_ontology_property(project, ontology_property)
    return ontology_property


@router.get("/properties", response_model=list[OntologyPropertyRead])
def list_ontology_properties(project_id: int, db: Session = Depends(get_db)) -> list[OntologyProperty]:
    _get_project_or_404(project_id, db)
    query = select(OntologyProperty).where(OntologyProperty.project_id == project_id).order_by(OntologyProperty.id.desc())
    return list(db.scalars(query).all())


@router.patch("/properties/{property_id}", response_model=OntologyPropertyRead)
def update_ontology_property(
    project_id: int,
    property_id: int,
    payload: OntologyPropertyUpdate,
    db: Session = Depends(get_db),
) -> OntologyProperty:
    project = _get_project_or_404(project_id, db)
    ontology_property = _get_project_property_or_404(project_id, property_id, db)

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] and updates["name"] != ontology_property.name:
        existing = db.scalar(
            select(OntologyProperty).where(
                OntologyProperty.project_id == project_id,
                OntologyProperty.name == updates["name"],
                OntologyProperty.id != property_id,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Another ontology property with this name already exists.")

    if "domain_class_id" in updates and updates["domain_class_id"] is not None:
        _get_project_class_or_404(project_id, updates["domain_class_id"], db)
    if "range_class_id" in updates and updates["range_class_id"] is not None:
        _get_project_class_or_404(project_id, updates["range_class_id"], db)

    property_type = updates.get("property_type", ontology_property.property_type)
    range_datatype = updates.get("range_datatype", ontology_property.range_datatype)
    if property_type == "data" and not range_datatype:
        raise HTTPException(status_code=400, detail="Data properties should include range_datatype.")
    if property_type == "data" and "range_class_id" not in updates:
        ontology_property.range_class_id = None

    for field, value in updates.items():
        setattr(ontology_property, field, value)

    db.commit()
    db.refresh(ontology_property)
    _safe_sync_ontology_property(project, ontology_property)
    return ontology_property
