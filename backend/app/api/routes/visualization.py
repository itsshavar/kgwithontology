from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kg_entity import KGEntity
from app.models.ontology_class import OntologyClass
from app.models.project import Project
from app.models.relation_instance import RelationInstance
from app.models.source_document import SourceDocument
from app.schemas.operations import VisualizationResponse

router = APIRouter(prefix="/projects/{project_id}/visualization", tags=["visualization"])


@router.get("", response_model=VisualizationResponse)
def get_visualization(project_id: int, db: Session = Depends(get_db)) -> VisualizationResponse:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    entities = list(db.scalars(select(KGEntity).where(KGEntity.project_id == project_id).limit(500)).all())
    relations = list(db.scalars(select(RelationInstance).where(RelationInstance.project_id == project_id).limit(1000)).all())
    classes = list(db.scalars(select(OntologyClass).where(OntologyClass.project_id == project_id).limit(500)).all())
    documents = list(db.scalars(select(SourceDocument).where(SourceDocument.project_id == project_id).limit(200)).all())
    nodes = [{"id": f"entity:{entity.id}", "label": entity.canonical_name, "type": "entity", "confidence": entity.confidence} for entity in entities]
    nodes.extend({"id": f"class:{cls.id}", "label": cls.label or cls.name, "type": "ontology_class"} for cls in classes)
    edges = []
    for relation in relations:
        if relation.subject_entity_id and relation.object_entity_id:
            edges.append({"source": f"entity:{relation.subject_entity_id}", "target": f"entity:{relation.object_entity_id}", "label": str(relation.predicate_id), "confidence": relation.confidence})
    ontology_tree = [{"id": cls.id, "label": cls.label or cls.name, "parent_id": cls.parent_class_id} for cls in classes]
    timeline = [{"id": doc.id, "label": doc.filename, "created_at": doc.created_at.isoformat() if doc.created_at else None, "type": "document"} for doc in documents]
    return VisualizationResponse(nodes=nodes, edges=edges, ontology_tree=ontology_tree, timeline=timeline)
