import json
import re
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.kg_entity import KGEntity
from app.models.ontology_class import OntologyClass
from app.models.ontology_property import OntologyProperty
from app.models.project import Project
from app.models.relation_instance import RelationInstance
from app.models.source_document import SourceDocument
from app.services.extraction.nlp_pipeline import get_hybrid_extraction_pipeline
from app.services.graph.neo4j_service import neo4j_service


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _normalize_property_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", cleaned).strip("_") or "related_to"


def _title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[_\s-]+", value) if part)


def _clean_entity_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" \t\n\r.,;:!?()[]{}\"'"))


def _guess_datatype(value: str) -> str:
    stripped = value.strip()
    if re.fullmatch(r"[-+]?\d+", stripped):
        return "integer"
    if re.fullmatch(r"[-+]?\d+\.\d+", stripped):
        return "decimal"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stripped):
        return "date"
    if re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", stripped):
        return "string"
    if stripped.lower() in {"true", "false"}:
        return "boolean"
    return "string"


def _build_class_lookup(classes: Iterable[OntologyClass]) -> dict[str, OntologyClass]:
    lookup: dict[str, OntologyClass] = {}
    for ontology_class in classes:
        lookup[_normalize_key(ontology_class.name)] = ontology_class
        if ontology_class.label:
            lookup[_normalize_key(ontology_class.label)] = ontology_class
    return lookup


def _build_property_lookup(properties: Iterable[OntologyProperty]) -> dict[str, OntologyProperty]:
    lookup: dict[str, OntologyProperty] = {}
    for ontology_property in properties:
        lookup[_normalize_key(ontology_property.name)] = ontology_property
        lookup[_normalize_key(_normalize_property_name(ontology_property.name))] = ontology_property
        if ontology_property.label:
            lookup[_normalize_key(ontology_property.label)] = ontology_property
            lookup[_normalize_key(_normalize_property_name(ontology_property.label))] = ontology_property
    return lookup


def _safe_sync_entity(project: Project, entity: KGEntity) -> None:
    try:
        neo4j_service.sync_entity(project, entity)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j entity sync warning: {exc}")


def _safe_sync_property(project: Project, ontology_property: OntologyProperty) -> None:
    try:
        neo4j_service.sync_ontology_property(project, ontology_property)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j ontology property sync warning: {exc}")


def _safe_sync_relation(project: Project, relation: RelationInstance) -> None:
    try:
        neo4j_service.sync_relation_instance(project, relation)
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j relation sync warning: {exc}")


def extract_kg_from_documents(
    *,
    project: Project,
    documents: list[SourceDocument],
    db: Session,
) -> dict[str, object]:
    classes = list(db.scalars(select(OntologyClass).where(OntologyClass.project_id == project.id)).all())
    properties = list(db.scalars(select(OntologyProperty).where(OntologyProperty.project_id == project.id)).all())
    entities = list(db.scalars(select(KGEntity).where(KGEntity.project_id == project.id)).all())
    existing_relations = list(
        db.scalars(select(RelationInstance).where(RelationInstance.project_id == project.id)).all()
    )

    class_lookup = _build_class_lookup(classes)
    property_lookup = _build_property_lookup(properties)
    entity_lookup: dict[str, KGEntity] = {_normalize_key(entity.canonical_name): entity for entity in entities}
    relation_keys: set[tuple[int, int, int | None, str | None, int | None]] = {
        (
            relation.subject_entity_id,
            relation.predicate_id,
            relation.object_entity_id,
            relation.object_value,
            relation.source_document_id,
        )
        for relation in existing_relations
    }

    created_entities = 0
    reused_entities = 0
    typed_entities = 0
    created_relations = 0
    created_properties = 0
    to_sync_entities: dict[int, KGEntity] = {}
    to_sync_properties: dict[int, OntologyProperty] = {}
    to_sync_relations: list[RelationInstance] = []
    extraction_pipeline = get_hybrid_extraction_pipeline()

    def get_or_create_entity(name: str, ontology_class: OntologyClass | None = None, confidence: float = 0.55) -> KGEntity:
        nonlocal created_entities, reused_entities, typed_entities

        cleaned_name = _clean_entity_name(name)
        key = _normalize_key(cleaned_name)
        entity = entity_lookup.get(key)
        if entity is None:
            entity = KGEntity(
                project_id=project.id,
                ontology_class_id=ontology_class.id if ontology_class else None,
                canonical_name=cleaned_name,
                aliases_json=json.dumps([]),
                source="auto-extracted",
                confidence=confidence,
            )
            db.add(entity)
            db.flush()
            entity_lookup[key] = entity
            created_entities += 1
            to_sync_entities[entity.id] = entity
        else:
            reused_entities += 1
            if ontology_class and entity.ontology_class_id is None:
                entity.ontology_class_id = ontology_class.id
                typed_entities += 1
                to_sync_entities[entity.id] = entity
        return entity

    def get_or_create_property(
        phrase: str,
        *,
        property_type: str,
        domain_class_id: int | None = None,
        range_class_id: int | None = None,
        range_datatype: str | None = None,
    ) -> OntologyProperty:
        nonlocal created_properties

        normalized_name = _normalize_property_name(phrase)
        lookup_keys = {
            _normalize_key(phrase),
            _normalize_key(normalized_name),
            _normalize_key(_title_case(phrase)),
        }
        ontology_property = None
        for key in lookup_keys:
            ontology_property = property_lookup.get(key)
            if ontology_property:
                break

        if ontology_property is None:
            ontology_property = OntologyProperty(
                project_id=project.id,
                name=normalized_name,
                label=_title_case(phrase),
                description=f"Auto-created from extraction phrase '{phrase}'.",
                property_type=property_type,
                domain_class_id=domain_class_id,
                range_class_id=range_class_id,
                range_datatype=range_datatype,
                status="candidate",
                confidence=0.5,
            )
            db.add(ontology_property)
            db.flush()
            created_properties += 1
        else:
            if domain_class_id and ontology_property.domain_class_id is None:
                ontology_property.domain_class_id = domain_class_id
            if property_type == "object" and range_class_id and ontology_property.range_class_id is None:
                ontology_property.range_class_id = range_class_id
            if property_type == "data" and range_datatype and not ontology_property.range_datatype:
                ontology_property.range_datatype = range_datatype

        property_lookup[_normalize_key(ontology_property.name)] = ontology_property
        property_lookup[_normalize_key(_normalize_property_name(ontology_property.name))] = ontology_property
        if ontology_property.label:
            property_lookup[_normalize_key(ontology_property.label)] = ontology_property
            property_lookup[_normalize_key(_normalize_property_name(ontology_property.label))] = ontology_property
        to_sync_properties[ontology_property.id] = ontology_property
        return ontology_property

    def maybe_create_relation(
        *,
        subject: KGEntity,
        predicate: OntologyProperty,
        document_id: int,
        evidence_text: str,
        object_entity: KGEntity | None = None,
        object_value: str | None = None,
    ) -> None:
        nonlocal created_relations

        relation_key = (
            subject.id,
            predicate.id,
            object_entity.id if object_entity else None,
            object_value,
            document_id,
        )
        if relation_key in relation_keys:
            return

        relation = RelationInstance(
            project_id=project.id,
            subject_entity_id=subject.id,
            predicate_id=predicate.id,
            object_entity_id=object_entity.id if object_entity else None,
            object_value=object_value,
            evidence_text=evidence_text,
            source_document_id=document_id,
            confidence=0.5,
        )
        db.add(relation)
        db.flush()
        relation_keys.add(relation_key)
        created_relations += 1
        to_sync_relations.append(relation)

    for document in documents:
        text = (document.raw_text or "").strip()
        if not text:
            continue

        analysis = extraction_pipeline.analyze_document(
            text,
            known_properties=[ontology_property.name for ontology_property in properties],
        )

        for mention in analysis.entity_mentions:
            normalized_mention = _normalize_key(mention.text)
            if normalized_mention in class_lookup and " " not in mention.text:
                continue
            get_or_create_entity(mention.text)

        for typed_candidate in analysis.typed_entities:
            ontology_class = class_lookup.get(_normalize_key(typed_candidate.class_name))
            if ontology_class is None:
                continue
            get_or_create_entity(typed_candidate.subject, ontology_class)

        for relation_candidate in analysis.object_relations:
            subject_entity = get_or_create_entity(relation_candidate.subject)
            object_entity = get_or_create_entity(relation_candidate.object_name)
            predicate = get_or_create_property(
                relation_candidate.predicate,
                property_type="object",
                domain_class_id=subject_entity.ontology_class_id,
                range_class_id=object_entity.ontology_class_id,
            )
            if predicate.domain_class_id and subject_entity.ontology_class_id is None:
                subject_entity.ontology_class_id = predicate.domain_class_id
                typed_entities += 1
                to_sync_entities[subject_entity.id] = subject_entity
            if predicate.range_class_id and object_entity.ontology_class_id is None:
                object_entity.ontology_class_id = predicate.range_class_id
                typed_entities += 1
                to_sync_entities[object_entity.id] = object_entity
            maybe_create_relation(
                subject=subject_entity,
                predicate=predicate,
                document_id=document.id,
                evidence_text=relation_candidate.sentence,
                object_entity=object_entity,
            )

        for data_candidate in analysis.data_relations:
            subject_entity = get_or_create_entity(data_candidate.subject)
            predicate = get_or_create_property(
                data_candidate.attribute,
                property_type="data",
                domain_class_id=subject_entity.ontology_class_id,
                range_datatype=_guess_datatype(data_candidate.value),
            )
            maybe_create_relation(
                subject=subject_entity,
                predicate=predicate,
                document_id=document.id,
                evidence_text=data_candidate.sentence,
                object_value=data_candidate.value,
            )

    db.commit()

    for entity in to_sync_entities.values():
        _safe_sync_entity(project, entity)
    for ontology_property in to_sync_properties.values():
        _safe_sync_property(project, ontology_property)
    for relation in to_sync_relations:
        _safe_sync_relation(project, relation)

    processed_document_ids = [document.id for document in documents]
    return {
        "project_id": project.id,
        "processed_documents": len(processed_document_ids),
        "document_ids": processed_document_ids,
        "created_entities": created_entities,
        "reused_entities": reused_entities,
        "typed_entities": typed_entities,
        "created_relations": created_relations,
        "created_properties": created_properties,
        "message": "Knowledge graph extraction completed with hybrid spaCy / transformer / optional LLM pipeline.",
    }
