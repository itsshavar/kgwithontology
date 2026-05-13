import json

from app.models.kg_entity import KGEntity
from app.schemas.kg import EntityRead, RelationInstanceRead
from app.models.relation_instance import RelationInstance


def entity_to_read(entity: KGEntity) -> EntityRead:
    aliases: list[str] = []
    if entity.aliases_json:
        try:
            parsed = json.loads(entity.aliases_json)
            if isinstance(parsed, list):
                aliases = [str(item) for item in parsed]
        except json.JSONDecodeError:
            aliases = []

    return EntityRead(
        id=entity.id,
        project_id=entity.project_id,
        ontology_class_id=entity.ontology_class_id,
        canonical_name=entity.canonical_name,
        aliases=aliases,
        confidence=entity.confidence,
        source=entity.source,
        created_at=entity.created_at,
    )


def relation_to_read(relation: RelationInstance) -> RelationInstanceRead:
    return RelationInstanceRead(
        id=relation.id,
        project_id=relation.project_id,
        subject_entity_id=relation.subject_entity_id,
        predicate_id=relation.predicate_id,
        object_entity_id=relation.object_entity_id,
        object_value=relation.object_value,
        evidence_text=relation.evidence_text,
        source_document_id=relation.source_document_id,
        confidence=relation.confidence,
        created_at=relation.created_at,
    )
