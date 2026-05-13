import json
import re
from collections import Counter

from app.models.domain_profile import DomainProfile
from app.models.source_document import SourceDocument
from app.schemas.ontology import OntologyCandidate, OntologyGenerateResponse
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

    return OntologyGenerateResponse(
        project_id=project_id,
        total_documents=len(documents),
        total_chunks=total_chunks,
        candidates=candidates,
    )
