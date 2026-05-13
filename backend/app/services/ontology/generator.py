import json
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain_profile import DomainProfile
from app.models.ontology_class import OntologyClass
from app.models.ontology_property import OntologyProperty
from app.models.project import Project
from app.models.relation_instance import RelationInstance
from app.models.source_document import SourceDocument
from app.schemas.ontology import OntologyCandidate, OntologyGenerateResponse, OntologyPropertyCandidate
from app.services.ingestion.text_chunker import chunk_text

STOP_WORDS = {
    "about", "after", "all", "also", "and", "any", "are", "because", "been",
    "before", "between", "both", "but", "can", "data", "document", "each",
    "from", "have", "into", "more", "must", "onto", "other", "over", "same",
    "should", "some", "such", "than", "that", "their", "them", "there", "these",
    "they", "this", "those", "through", "using", "used", "uses", "when", "where",
    "which", "with", "within", "would", "your",
}


def generate_candidates(
    *,
    project_id: int,
    documents: list[SourceDocument],
    domain_profile: DomainProfile | None = None,
    max_candidates: int = 15,
    min_term_length: int = 4,
    db: Session | None = None,
) -> OntologyGenerateResponse:
    token_counter: Counter[str] = Counter()
    evidence_lookup: dict[str, str] = {}
    total_chunks = 0

    seed_classes: set[str] = set()
    if domain_profile and domain_profile.seed_schema:
        try:
            parsed = json.loads(domain_profile.seed_schema)
            seed_classes = {item.lower() for item in parsed.get("seed_classes", []) if isinstance(item, str)}
        except json.JSONDecodeError:
            seed_classes = set()

    for document in documents:
        text = (document.raw_text or "").strip()
        if not text:
            continue

        chunks = chunk_text(text)
        total_chunks += len(chunks)

        sentences = re.split(r"(?<=[.!?])\s+", text)
        tokens = re.findall(r"\b[a-zA-Z][a-zA-Z\-]{%d,}\b" % (min_term_length - 1), text.lower())
        for token in tokens:
            if token in STOP_WORDS:
                continue
            token_counter[token] += 1
            if token not in evidence_lookup:
                evidence_lookup[token] = next((s for s in sentences if token in s.lower()), text[:200])

    candidates: list[OntologyCandidate] = []
    for term, frequency in token_counter.most_common(max_candidates):
        suggested_type = "SeedClassCandidate" if term in seed_classes else "ClassCandidate"
        candidates.append(
            OntologyCandidate(
                term=term,
                frequency=frequency,
                suggested_type=suggested_type,
                evidence=evidence_lookup.get(term),
            )
        )

    property_candidates: list[OntologyPropertyCandidate] = []
    if db:
        # Get property frequencies from relations
        relations = list(db.scalars(select(RelationInstance).where(RelationInstance.project_id == project_id)).all())
        property_counter: Counter[str] = Counter()
        property_evidence: dict[str, str] = {}
        for relation in relations:
            property_obj = db.get(OntologyProperty, relation.predicate_id)
            if property_obj:
                prop_name = property_obj.name
                property_counter[prop_name] += 1
                if prop_name not in property_evidence:
                    property_evidence[prop_name] = relation.evidence_text or ""

        for term, frequency in property_counter.most_common(max_candidates):
            property_candidates.append(
                OntologyPropertyCandidate(
                    term=term,
                    frequency=frequency,
                    evidence=property_evidence.get(term),
                )
            )

    return OntologyGenerateResponse(
        project_id=project_id,
        total_documents=len(documents),
        total_chunks=total_chunks,
        candidates=candidates,
        property_candidates=property_candidates,
    )


def auto_generate_ontology(
    *,
    project: Project,
    documents: list[SourceDocument],
    domain_profile: DomainProfile | None = None,
    max_candidates: int = 15,
    min_term_length: int = 4,
    db: Session,
) -> OntologyGenerateResponse:
    response = generate_candidates(
        project_id=project.id,
        documents=documents,
        domain_profile=domain_profile,
        max_candidates=max_candidates,
        min_term_length=min_term_length,
        db=db,
    )

    # Create classes
    for candidate in response.candidates:
        # Check if class already exists
        existing = db.scalar(
            select(OntologyClass).where(
                OntologyClass.project_id == project.id,
                OntologyClass.name == candidate.term
            )
        )
        if not existing:
            ontology_class = OntologyClass(
                project_id=project.id,
                name=candidate.term,
                label=candidate.term.title(),
                description=f"Auto-generated from document analysis. Evidence: {candidate.evidence}",
                status="candidate",
                source="auto-extracted",
                confidence=candidate.frequency / 10.0,  # rough confidence
            )
            db.add(ontology_class)
            db.flush()
            # Sync to graph
            from app.services.graph.neo4j_service import neo4j_service
            try:
                neo4j_service.sync_ontology_class(project, ontology_class)
            except Exception as exc:
                print(f"Neo4j ontology class sync warning: {exc}")

    # Properties are already created during KG extraction, so no need to create again

    return response
