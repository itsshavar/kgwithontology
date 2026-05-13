from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kg_entity import KGEntity
from app.models.ontology_class import OntologyClass
from app.models.ontology_property import OntologyProperty
from app.models.project import Project
from app.models.relation_instance import RelationInstance
from app.schemas.graph import GraphHealthResponse, GraphSyncResponse
from app.schemas.graph_view import GraphEdge, GraphNode, GraphViewResponse
from app.services.graph.neo4j_service import neo4j_service

router = APIRouter(tags=["graph"])


@router.get("/graph/health", response_model=GraphHealthResponse)
def graph_health() -> GraphHealthResponse:
    return GraphHealthResponse(**neo4j_service.health())


@router.get("/api/v1/projects/{project_id}/graph/view", response_model=GraphViewResponse)
def get_project_graph_view(project_id: int, db: Session = Depends(get_db)) -> GraphViewResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    ontology_classes = list(
        db.scalars(select(OntologyClass).where(OntologyClass.project_id == project_id)).all()
    )
    ontology_properties = list(
        db.scalars(select(OntologyProperty).where(OntologyProperty.project_id == project_id)).all()
    )
    entities = list(db.scalars(select(KGEntity).where(KGEntity.project_id == project_id)).all())
    relations = list(
        db.scalars(select(RelationInstance).where(RelationInstance.project_id == project_id)).all()
    )

    class_lookup = {item.id: item for item in ontology_classes}
    property_lookup = {item.id: item for item in ontology_properties}
    entity_lookup = {item.id: item for item in entities}

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    seen_nodes: set[str] = set()

    def add_node(node: GraphNode) -> None:
        if node.id in seen_nodes:
            return
        seen_nodes.add(node.id)
        nodes.append(node)

    for ontology_class in ontology_classes:
        add_node(
            GraphNode(
                id=f"class-{ontology_class.id}",
                label=ontology_class.label or ontology_class.name,
                node_type="ontology_class",
                metadata={
                    "class_id": ontology_class.id,
                    "name": ontology_class.name,
                    "status": ontology_class.status,
                    "source": ontology_class.source,
                },
            )
        )
        if ontology_class.parent_class_id:
            edges.append(
                GraphEdge(
                    id=f"subclass-{ontology_class.id}-{ontology_class.parent_class_id}",
                    source=f"class-{ontology_class.id}",
                    target=f"class-{ontology_class.parent_class_id}",
                    label="subclass_of",
                    edge_type="ontology_hierarchy",
                    metadata={"parent_class_id": ontology_class.parent_class_id},
                )
            )

    for ontology_property in ontology_properties:
        if ontology_property.domain_class_id and ontology_property.range_class_id:
            edges.append(
                GraphEdge(
                    id=f"ontology-property-{ontology_property.id}",
                    source=f"class-{ontology_property.domain_class_id}",
                    target=f"class-{ontology_property.range_class_id}",
                    label=ontology_property.label or ontology_property.name,
                    edge_type="ontology_property",
                    metadata={
                        "property_id": ontology_property.id,
                        "property_type": ontology_property.property_type,
                    },
                )
            )
        elif ontology_property.property_type == "data" and ontology_property.domain_class_id and ontology_property.range_datatype:
            datatype_node_id = f"datatype-{ontology_property.id}"
            add_node(
                GraphNode(
                    id=datatype_node_id,
                    label=ontology_property.range_datatype,
                    node_type="datatype",
                    metadata={"property_id": ontology_property.id},
                )
            )
            edges.append(
                GraphEdge(
                    id=f"ontology-datatype-{ontology_property.id}",
                    source=f"class-{ontology_property.domain_class_id}",
                    target=datatype_node_id,
                    label=ontology_property.label or ontology_property.name,
                    edge_type="ontology_property",
                    metadata={
                        "property_id": ontology_property.id,
                        "property_type": ontology_property.property_type,
                    },
                )
            )

    for entity in entities:
        add_node(
            GraphNode(
                id=f"entity-{entity.id}",
                label=entity.canonical_name,
                node_type="entity",
                metadata={
                    "entity_id": entity.id,
                    "ontology_class_id": entity.ontology_class_id,
                    "source": entity.source,
                },
            )
        )
        if entity.ontology_class_id and entity.ontology_class_id in class_lookup:
            edges.append(
                GraphEdge(
                    id=f"instance-of-{entity.id}-{entity.ontology_class_id}",
                    source=f"entity-{entity.id}",
                    target=f"class-{entity.ontology_class_id}",
                    label="instance_of",
                    edge_type="entity_typing",
                    metadata={"entity_id": entity.id, "class_id": entity.ontology_class_id},
                )
            )

    for relation in relations:
        target_id = ""
        if relation.object_entity_id and relation.object_entity_id in entity_lookup:
            target_id = f"entity-{relation.object_entity_id}"
        elif relation.object_value:
            literal_id = f"literal-{relation.id}"
            target_id = literal_id
            add_node(
                GraphNode(
                    id=literal_id,
                    label=relation.object_value,
                    node_type="literal",
                    metadata={"relation_id": relation.id},
                )
            )
        else:
            continue

        predicate = property_lookup.get(relation.predicate_id)
        edges.append(
            GraphEdge(
                id=f"relation-{relation.id}",
                source=f"entity-{relation.subject_entity_id}",
                target=target_id,
                label=predicate.label or predicate.name if predicate else f"property:{relation.predicate_id}",
                edge_type="relation_instance",
                metadata={
                    "relation_id": relation.id,
                    "predicate_id": relation.predicate_id,
                    "confidence": relation.confidence,
                    "evidence_text": relation.evidence_text,
                    "source_document_id": relation.source_document_id,
                },
            )
        )

    return GraphViewResponse(
        project_id=project_id,
        nodes=nodes,
        edges=edges,
        ontology_class_count=len(ontology_classes),
        ontology_property_count=len(ontology_properties),
        entity_count=len(entities),
        relation_count=len(relations),
    )


@router.post("/api/v1/projects/{project_id}/graph/sync", response_model=GraphSyncResponse)
def sync_project_graph(project_id: int, db: Session = Depends(get_db)) -> GraphSyncResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not neo4j_service.enabled:
        return GraphSyncResponse(
            project_id=project_id,
            graph_enabled=False,
            synced=False,
            ontology_classes=0,
            ontology_properties=0,
            entities=0,
            relation_instances=0,
            message="Neo4j is not configured. Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD.",
        )

    ontology_classes = list(
        db.scalars(select(OntologyClass).where(OntologyClass.project_id == project_id)).all()
    )
    ontology_properties = list(
        db.scalars(select(OntologyProperty).where(OntologyProperty.project_id == project_id)).all()
    )
    entities = list(db.scalars(select(KGEntity).where(KGEntity.project_id == project_id)).all())
    relations = list(
        db.scalars(select(RelationInstance).where(RelationInstance.project_id == project_id)).all()
    )

    try:
        neo4j_service.initialize_schema()
        neo4j_service.sync_project(project)
        for ontology_class in ontology_classes:
            neo4j_service.sync_ontology_class(project, ontology_class)
        for ontology_property in ontology_properties:
            neo4j_service.sync_ontology_property(project, ontology_property)
        for entity in entities:
            neo4j_service.sync_entity(project, entity)
        for relation in relations:
            neo4j_service.sync_relation_instance(project, relation)
    except Exception as exc:  # pragma: no cover - runtime integration path
        raise HTTPException(status_code=502, detail=f"Neo4j sync failed: {exc}") from exc

    return GraphSyncResponse(
        project_id=project_id,
        graph_enabled=True,
        synced=True,
        ontology_classes=len(ontology_classes),
        ontology_properties=len(ontology_properties),
        entities=len(entities),
        relation_instances=len(relations),
        message="Project ontology and KG records synced to Neo4j.",
    )
