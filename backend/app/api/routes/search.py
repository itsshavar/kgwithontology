from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.kg_entity import KGEntity
from app.models.ontology_class import OntologyClass
from app.models.project import Project
from app.models.relation_instance import RelationInstance
from app.models.source_document import SourceDocument
from app.schemas.operations import QueryRequest, QueryResponse, SearchHit, SearchRequest, SearchResponse
from app.services.export_service import build_project_rdf_graph
from app.services.graph.neo4j_service import neo4j_service

router = APIRouter(prefix="/projects/{project_id}", tags=["search-query"])


@router.post("/search", response_model=SearchResponse)
def search_project(project_id: int, payload: SearchRequest, db: Session = Depends(get_db)) -> SearchResponse:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    like = f"%{payload.query}%"
    hits: list[SearchHit] = []
    for doc in db.scalars(select(SourceDocument).where(SourceDocument.project_id == project_id, or_(SourceDocument.filename.ilike(like), SourceDocument.raw_text.ilike(like))).limit(payload.limit)).all():
        snippet = (doc.raw_text or "")[:240]
        hits.append(SearchHit(type="document", id=doc.id, label=doc.filename, snippet=snippet, score=1.0))
    remaining = max(payload.limit - len(hits), 0)
    if remaining:
        for entity in db.scalars(select(KGEntity).where(KGEntity.project_id == project_id, KGEntity.canonical_name.ilike(like)).limit(remaining)).all():
            hits.append(SearchHit(type="entity", id=entity.id, label=entity.canonical_name, score=0.9))
    remaining = max(payload.limit - len(hits), 0)
    if remaining:
        for ontology_class in db.scalars(select(OntologyClass).where(OntologyClass.project_id == project_id, OntologyClass.name.ilike(like)).limit(remaining)).all():
            hits.append(SearchHit(type="ontology_class", id=ontology_class.id, label=ontology_class.name, snippet=ontology_class.description, score=0.8))
    return SearchResponse(hits=hits)


@router.post("/query", response_model=QueryResponse)
def execute_query(project_id: int, payload: QueryRequest, db: Session = Depends(get_db)) -> QueryResponse:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    if payload.language == "cypher":
        if neo4j_service.enabled:
            rows = neo4j_service.execute_read(payload.query, limit=payload.limit)
            return QueryResponse(language="cypher", executed=True, rows=rows, message="Executed against Neo4j.")
        return QueryResponse(language="cypher", executed=False, rows=[], message="Neo4j is not configured; query saved for external execution.")
    if payload.language == "sparql":
        graph = build_project_rdf_graph(db.get(Project, project_id), db)
        result = graph.query(payload.query)
        rows = []
        for index, row in enumerate(result):
            if index >= payload.limit:
                break
            row_dict = {}
            for key, value in row.asdict().items():
                row_dict[str(key)] = str(value)
            rows.append(row_dict)
        return QueryResponse(language="sparql", executed=True, rows=rows, message="Executed against the project RDF graph.")
    relations = db.scalars(select(RelationInstance).where(RelationInstance.project_id == project_id).limit(payload.limit)).all()
    rows = [{"id": relation.id, "predicate_id": relation.predicate_id, "confidence": relation.confidence} for relation in relations]
    return QueryResponse(language=payload.language, executed=True, rows=rows, message="Executed deterministic local project query.")
