import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kg_entity import KGEntity
from app.models.ontology_class import OntologyClass
from app.models.ontology_property import OntologyProperty
from app.models.project import Project
from app.models.relation_instance import RelationInstance
from app.models.source_document import SourceDocument
from app.schemas.converters import entity_to_read, relation_to_read
from app.schemas.extraction import KGExtractionRunResponse
from app.schemas.kg import (
    EntityCreate,
    EntityRead,
    RelationEvidenceRead,
    RelationInstanceCreate,
    RelationInstanceRead,
    RelationInstanceUpdate,
)
from app.services.extraction.document_kg_extractor import extract_kg_from_documents
from app.services.graph.neo4j_service import neo4j_service

router = APIRouter(prefix="/projects/{project_id}/kg", tags=["knowledge-graph"])


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


def _get_project_entity_or_404(project_id: int, entity_id: int, db: Session) -> KGEntity:
    entity = db.get(KGEntity, entity_id)
    if not entity or entity.project_id != project_id:
        raise HTTPException(status_code=404, detail="Entity not found in this project.")
    return entity


def _get_project_relation_or_404(project_id: int, relation_id: int, db: Session) -> RelationInstance:
    relation = db.get(RelationInstance, relation_id)
    if not relation or relation.project_id != project_id:
        raise HTTPException(status_code=404, detail="Relation not found in this project.")
    return relation


def _safe_sync_entity(project: Project, entity: KGEntity) -> None:
    try:
        neo4j_service.sync_entity(project, entity)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j entity sync warning: {exc}")


def _safe_sync_relation(project: Project, relation: RelationInstance) -> None:
    try:
        neo4j_service.sync_relation_instance(project, relation)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j relation sync warning: {exc}")


def _compute_evidence_preview(document_text: str, evidence_text: str | None) -> tuple[str, str, str, int | None, int | None]:
    if not document_text:
        return "", evidence_text or "", "", None, None
    if not evidence_text:
        preview = document_text[:800]
        return "", preview, document_text[800:1200], 0, min(len(preview), len(document_text))

    exact_index = document_text.find(evidence_text)
    if exact_index < 0:
        exact_index = document_text.lower().find(evidence_text.lower())

    if exact_index < 0:
        return "", evidence_text, "", None, None

    start = exact_index
    end = exact_index + len(evidence_text)
    before_start = max(0, start - 180)
    after_end = min(len(document_text), end + 180)
    return document_text[before_start:start], document_text[start:end], document_text[end:after_end], start, end


@router.post("/extract", response_model=KGExtractionRunResponse)
def extract_project_kg(
    project_id: int,
    document_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> KGExtractionRunResponse:
    project = _get_project_or_404(project_id, db)

    if document_id is not None:
        document = db.get(SourceDocument, document_id)
        if not document or document.project_id != project_id:
            raise HTTPException(status_code=404, detail="Source document not found in this project.")
        documents = [document]
    else:
        documents = list(
            db.scalars(select(SourceDocument).where(SourceDocument.project_id == project_id)).all()
        )

    if not documents:
        raise HTTPException(status_code=400, detail="No documents available for extraction.")

    result = extract_kg_from_documents(project=project, documents=documents, db=db)
    return KGExtractionRunResponse(**result)


@router.post("/entities", response_model=EntityRead, status_code=status.HTTP_201_CREATED)
def create_entity(
    project_id: int,
    payload: EntityCreate,
    db: Session = Depends(get_db),
) -> EntityRead:
    project = _get_project_or_404(project_id, db)

    if payload.ontology_class_id is not None:
        _get_project_class_or_404(project_id, payload.ontology_class_id, db)

    entity = KGEntity(
        project_id=project_id,
        ontology_class_id=payload.ontology_class_id,
        canonical_name=payload.canonical_name,
        aliases_json=json.dumps(payload.aliases),
        confidence=payload.confidence,
        source=payload.source,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    _safe_sync_entity(project, entity)
    return entity_to_read(entity)


@router.get("/entities", response_model=list[EntityRead])
def list_entities(project_id: int, db: Session = Depends(get_db)) -> list[EntityRead]:
    _get_project_or_404(project_id, db)
    query = select(KGEntity).where(KGEntity.project_id == project_id).order_by(KGEntity.id.desc())
    entities = list(db.scalars(query).all())
    return [entity_to_read(entity) for entity in entities]


@router.post("/relations", response_model=RelationInstanceRead, status_code=status.HTTP_201_CREATED)
def create_relation_instance(
    project_id: int,
    payload: RelationInstanceCreate,
    db: Session = Depends(get_db),
) -> RelationInstanceRead:
    project = _get_project_or_404(project_id, db)

    _get_project_entity_or_404(project_id, payload.subject_entity_id, db)
    _get_project_property_or_404(project_id, payload.predicate_id, db)

    if payload.object_entity_id is None and payload.object_value is None:
        raise HTTPException(status_code=400, detail="Provide object_entity_id or object_value.")

    if payload.object_entity_id is not None:
        _get_project_entity_or_404(project_id, payload.object_entity_id, db)

    if payload.source_document_id is not None:
        document = db.get(SourceDocument, payload.source_document_id)
        if not document or document.project_id != project_id:
            raise HTTPException(status_code=404, detail="Source document not found in this project.")

    relation = RelationInstance(
        project_id=project_id,
        subject_entity_id=payload.subject_entity_id,
        predicate_id=payload.predicate_id,
        object_entity_id=payload.object_entity_id,
        object_value=payload.object_value,
        evidence_text=payload.evidence_text,
        source_document_id=payload.source_document_id,
        confidence=payload.confidence,
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)
    _safe_sync_relation(project, relation)
    return relation_to_read(relation)


@router.get("/relations", response_model=list[RelationInstanceRead])
def list_relation_instances(project_id: int, db: Session = Depends(get_db)) -> list[RelationInstanceRead]:
    _get_project_or_404(project_id, db)
    query = select(RelationInstance).where(RelationInstance.project_id == project_id).order_by(RelationInstance.id.desc())
    relations = list(db.scalars(query).all())
    return [relation_to_read(relation) for relation in relations]


@router.patch("/relations/{relation_id}", response_model=RelationInstanceRead)
def update_relation_instance(
    project_id: int,
    relation_id: int,
    payload: RelationInstanceUpdate,
    db: Session = Depends(get_db),
) -> RelationInstanceRead:
    project = _get_project_or_404(project_id, db)
    relation = _get_project_relation_or_404(project_id, relation_id, db)

    updates = payload.model_dump(exclude_unset=True)

    subject_entity_id = updates.get("subject_entity_id", relation.subject_entity_id)
    predicate_id = updates.get("predicate_id", relation.predicate_id)
    object_entity_id = updates.get("object_entity_id", relation.object_entity_id)
    object_value = updates.get("object_value", relation.object_value)
    source_document_id = updates.get("source_document_id", relation.source_document_id)

    _get_project_entity_or_404(project_id, subject_entity_id, db)
    _get_project_property_or_404(project_id, predicate_id, db)
    if object_entity_id is not None:
        _get_project_entity_or_404(project_id, object_entity_id, db)
    if object_entity_id is None and object_value is None:
        raise HTTPException(status_code=400, detail="Provide object_entity_id or object_value.")
    if source_document_id is not None:
        document = db.get(SourceDocument, source_document_id)
        if not document or document.project_id != project_id:
            raise HTTPException(status_code=404, detail="Source document not found in this project.")

    for field, value in updates.items():
        setattr(relation, field, value)

    db.commit()
    db.refresh(relation)
    _safe_sync_relation(project, relation)
    return relation_to_read(relation)


@router.get("/relations/{relation_id}/evidence", response_model=RelationEvidenceRead)
def get_relation_evidence(
    project_id: int,
    relation_id: int,
    db: Session = Depends(get_db),
) -> RelationEvidenceRead:
    relation = _get_project_relation_or_404(project_id, relation_id, db)
    source_document = None
    if relation.source_document_id is not None:
        source_document = db.get(SourceDocument, relation.source_document_id)
        if source_document and source_document.project_id != project_id:
            source_document = None

    document_text = (source_document.raw_text or "") if source_document else ""
    before, highlight, after, start_offset, end_offset = _compute_evidence_preview(document_text, relation.evidence_text)

    return RelationEvidenceRead(
        relation_id=relation.id,
        source_document_id=relation.source_document_id,
        source_filename=source_document.filename if source_document else None,
        evidence_text=relation.evidence_text,
        before=before,
        highlight=highlight,
        after=after,
        start_offset=start_offset,
        end_offset=end_offset,
    )
