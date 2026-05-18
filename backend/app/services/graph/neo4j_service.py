import json
from typing import Any

from neo4j import Driver, GraphDatabase

from app.core.config import settings
from app.models.kg_entity import KGEntity
from app.models.ontology_class import OntologyClass
from app.models.ontology_property import OntologyProperty
from app.models.project import Project
from app.models.relation_instance import RelationInstance


class Neo4jService:
    def __init__(self) -> None:
        self._driver: Driver | None = None

    @property
    def enabled(self) -> bool:
        return settings.neo4j_enabled

    def get_driver(self) -> Driver | None:
        if not self.enabled:
            return None

        if self._driver is None:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def health(self) -> dict[str, Any]:
        if not self.enabled:
            return {
                "enabled": False,
                "connected": False,
                "uri": settings.neo4j_uri,
                "database": settings.neo4j_database,
                "message": "Neo4j is not configured. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD.",
            }

        try:
            driver = self.get_driver()
            assert driver is not None
            driver.verify_connectivity()
            return {
                "enabled": True,
                "connected": True,
                "uri": settings.neo4j_uri,
                "database": settings.neo4j_database,
                "message": "Neo4j connection is healthy.",
            }
        except Exception as exc:  # pragma: no cover - runtime integration path
            return {
                "enabled": True,
                "connected": False,
                "uri": settings.neo4j_uri,
                "database": settings.neo4j_database,
                "message": f"Neo4j connectivity check failed: {exc}",
            }

    def initialize_schema(self) -> None:
        if not self.enabled:
            return

        driver = self.get_driver()
        if driver is None:
            return

        statements = [
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (n:Project) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT ontology_class_id IF NOT EXISTS FOR (n:OntologyClass) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT ontology_property_id IF NOT EXISTS FOR (n:OntologyProperty) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT relation_instance_id IF NOT EXISTS FOR (n:RelationInstance) REQUIRE n.id IS UNIQUE",
        ]

        with driver.session(database=settings.neo4j_database) as session:
            for statement in statements:
                session.run(statement)

    def sync_project(self, project: Project) -> None:
        if not self.enabled:
            return

        driver = self.get_driver()
        if driver is None:
            return

        payload = {
            "id": project.id,
            "name": project.name,
            "description": project.description,
        }
        query = """
        MERGE (p:Project {id: $id})
        SET p.name = $name,
            p.description = $description
        """
        with driver.session(database=settings.neo4j_database) as session:
            session.run(query, payload)

    def sync_ontology_class(self, project: Project, ontology_class: OntologyClass) -> None:
        if not self.enabled:
            return

        self.sync_project(project)
        driver = self.get_driver()
        if driver is None:
            return

        payload = {
            "project_id": project.id,
            "id": ontology_class.id,
            "name": ontology_class.name,
            "label": ontology_class.label,
            "description": ontology_class.description,
            "status": ontology_class.status,
            "source": ontology_class.source,
            "confidence": ontology_class.confidence,
            "parent_class_id": ontology_class.parent_class_id,
        }
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (c:OntologyClass {id: $id})
        SET c.project_id = $project_id,
            c.name = $name,
            c.label = $label,
            c.description = $description,
            c.status = $status,
            c.source = $source,
            c.confidence = $confidence
        MERGE (p)-[:HAS_ONTOLOGY_CLASS]->(c)
        WITH c
        OPTIONAL MATCH (c)-[old:SUBCLASS_OF]->(:OntologyClass)
        WITH c, collect(old) AS old_rels
        FOREACH (rel IN old_rels | DELETE rel)
        WITH c
        OPTIONAL MATCH (parent:OntologyClass {id: $parent_class_id})
        FOREACH (_ IN CASE WHEN parent IS NULL THEN [] ELSE [1] END |
            MERGE (c)-[:SUBCLASS_OF]->(parent)
        )
        """
        with driver.session(database=settings.neo4j_database) as session:
            session.run(query, payload)

    def sync_ontology_property(self, project: Project, ontology_property: OntologyProperty) -> None:
        if not self.enabled:
            return

        self.sync_project(project)
        driver = self.get_driver()
        if driver is None:
            return

        payload = {
            "project_id": project.id,
            "id": ontology_property.id,
            "name": ontology_property.name,
            "label": ontology_property.label,
            "description": ontology_property.description,
            "property_type": ontology_property.property_type,
            "domain_class_id": ontology_property.domain_class_id,
            "range_class_id": ontology_property.range_class_id,
            "range_datatype": ontology_property.range_datatype,
            "status": ontology_property.status,
            "confidence": ontology_property.confidence,
        }
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (prop:OntologyProperty {id: $id})
        SET prop.project_id = $project_id,
            prop.name = $name,
            prop.label = $label,
            prop.description = $description,
            prop.property_type = $property_type,
            prop.range_datatype = $range_datatype,
            prop.status = $status,
            prop.confidence = $confidence
        MERGE (p)-[:HAS_ONTOLOGY_PROPERTY]->(prop)
        WITH prop
        OPTIONAL MATCH (prop)-[oldDomain:HAS_DOMAIN]->(:OntologyClass)
        WITH prop, collect(oldDomain) AS old_domain_rels
        FOREACH (rel IN old_domain_rels | DELETE rel)
        WITH prop
        OPTIONAL MATCH (prop)-[oldRange:HAS_RANGE]->(:OntologyClass)
        WITH prop, collect(oldRange) AS old_range_rels
        FOREACH (rel IN old_range_rels | DELETE rel)
        WITH prop
        OPTIONAL MATCH (domain:OntologyClass {id: $domain_class_id})
        FOREACH (_ IN CASE WHEN domain IS NULL THEN [] ELSE [1] END |
            MERGE (prop)-[:HAS_DOMAIN]->(domain)
        )
        WITH prop
        OPTIONAL MATCH (range:OntologyClass {id: $range_class_id})
        FOREACH (_ IN CASE WHEN range IS NULL THEN [] ELSE [1] END |
            MERGE (prop)-[:HAS_RANGE]->(range)
        )
        """
        with driver.session(database=settings.neo4j_database) as session:
            session.run(query, payload)

    def sync_entity(self, project: Project, entity: KGEntity) -> None:
        if not self.enabled:
            return

        self.sync_project(project)
        driver = self.get_driver()
        if driver is None:
            return

        aliases: list[str] = []
        if entity.aliases_json:
            try:
                parsed = json.loads(entity.aliases_json)
                if isinstance(parsed, list):
                    aliases = [str(item) for item in parsed]
            except json.JSONDecodeError:
                aliases = []

        payload = {
            "project_id": project.id,
            "id": entity.id,
            "canonical_name": entity.canonical_name,
            "aliases": aliases,
            "confidence": entity.confidence,
            "source": entity.source,
            "ontology_class_id": entity.ontology_class_id,
        }
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (e:Entity {id: $id})
        SET e.project_id = $project_id,
            e.canonical_name = $canonical_name,
            e.aliases = $aliases,
            e.confidence = $confidence,
            e.source = $source
        MERGE (p)-[:HAS_ENTITY]->(e)
        WITH e
        OPTIONAL MATCH (e)-[old:INSTANCE_OF]->(:OntologyClass)
        WITH e, collect(old) AS old_rels
        FOREACH (rel IN old_rels | DELETE rel)
        WITH e
        OPTIONAL MATCH (c:OntologyClass {id: $ontology_class_id})
        FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END |
            MERGE (e)-[:INSTANCE_OF]->(c)
        )
        """
        with driver.session(database=settings.neo4j_database) as session:
            session.run(query, payload)

    def sync_relation_instance(self, project: Project, relation: RelationInstance) -> None:
        if not self.enabled:
            return

        self.sync_project(project)
        driver = self.get_driver()
        if driver is None:
            return

        payload = {
            "project_id": project.id,
            "id": relation.id,
            "subject_entity_id": relation.subject_entity_id,
            "predicate_id": relation.predicate_id,
            "object_entity_id": relation.object_entity_id,
            "object_value": relation.object_value,
            "evidence_text": relation.evidence_text,
            "source_document_id": relation.source_document_id,
            "confidence": relation.confidence,
        }
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (r:RelationInstance {id: $id})
        SET r.project_id = $project_id,
            r.object_value = $object_value,
            r.evidence_text = $evidence_text,
            r.source_document_id = $source_document_id,
            r.confidence = $confidence
        MERGE (p)-[:HAS_RELATION]->(r)
        WITH r
        OPTIONAL MATCH (:Entity)-[oldSubject:SOURCE_OF]->(r)
        WITH r, collect(oldSubject) AS old_subject_rels
        FOREACH (rel IN old_subject_rels | DELETE rel)
        WITH r
        OPTIONAL MATCH (r)-[oldPredicate:USES_PREDICATE]->(:OntologyProperty)
        WITH r, collect(oldPredicate) AS old_predicate_rels
        FOREACH (rel IN old_predicate_rels | DELETE rel)
        WITH r
        OPTIONAL MATCH (r)-[oldTarget:TARGETS]->(:Entity)
        WITH r, collect(oldTarget) AS old_target_rels
        FOREACH (rel IN old_target_rels | DELETE rel)
        WITH r
        MATCH (subject:Entity {id: $subject_entity_id})
        MERGE (subject)-[:SOURCE_OF]->(r)
        WITH r
        OPTIONAL MATCH (predicate:OntologyProperty {id: $predicate_id})
        FOREACH (_ IN CASE WHEN predicate IS NULL THEN [] ELSE [1] END |
            MERGE (r)-[:USES_PREDICATE]->(predicate)
        )
        WITH r
        OPTIONAL MATCH (target:Entity {id: $object_entity_id})
        FOREACH (_ IN CASE WHEN target IS NULL THEN [] ELSE [1] END |
            MERGE (r)-[:TARGETS]->(target)
        )
        """
        with driver.session(database=settings.neo4j_database) as session:
            session.run(query, payload)

    def execute_read(self, query: str, limit: int = 100) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        driver = self.get_driver()
        if driver is None:
            return []
        limited_query = query if "limit" in query.lower() else f"{query} LIMIT {int(limit)}"
        with driver.session(database=settings.neo4j_database) as session:
            result = session.run(limited_query)
            return [dict(record) for record in result]


neo4j_service = Neo4jService()
