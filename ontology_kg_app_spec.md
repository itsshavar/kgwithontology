# Domain-Aware Ontology Generator & Knowledge Graph Creator

## Working Title
**OntoForge** — a domain-aware platform for:
1. generating ontologies from domain definitions and documents,
2. extracting knowledge graphs from unstructured text,
3. linking graph facts back to source evidence,
4. iteratively refining ontology + KG with human review.

---

## 1. Product Vision
Build a Python-based application that helps users create **domain-specific ontologies** and **knowledge graphs** from:
- unstructured text,
- semi-structured data,
- domain glossaries and taxonomies,
- user-defined schema rules.

The product should not only extract entities and relations, but also:
- propose ontology classes and properties,
- align extracted facts to the ontology,
- keep provenance to the original text,
- support domain-specific customization,
- allow human-in-the-loop correction and approval.

---

## 2. Core Problem
Most KG tools either:
- extract triples from text without strong ontology alignment, or
- require experts to manually design the ontology first.

This application should bridge both worlds:
- **Ontology-first** enough for semantic consistency,
- **Text-driven** enough to learn from unstructured content,
- **Domain-aware** enough to adapt to specific verticals.

---

## 3. Goals
### Primary Goals
- Generate a draft ontology from domain documents and seed vocabularies.
- Extract entities, attributes, and relations from unstructured text.
- Map extracted facts to ontology classes and predicates.
- Store the resulting graph in a queryable graph database.
- Preserve evidence spans for every extracted triple.
- Let users review, merge, correct, and version ontology/KG outputs.

### Secondary Goals
- Support export to OWL/RDF/JSON-LD/CSV.
- Support confidence scoring and explainability.
- Provide domain packs/templates for different industries.

### Non-Goals for V1
- Fully autonomous ontology creation without human review.
- Large-scale distributed graph analytics.
- Real-time web-scale ingestion.
- Complex reasoning engines beyond basic validation and rule checks.

---

## 4. Target Users
### 1. Domain Experts
Need a fast way to structure knowledge from reports, manuals, contracts, policies, or research.

### 2. Data / Knowledge Engineers
Need ontology generation, mapping, graph construction, and export pipelines.

### 3. AI / NLP Teams
Need graph-grounded structured outputs from large document sets.

### 4. Enterprise Search / RAG Teams
Need better retrieval, entity resolution, and semantic grounding over enterprise text.

---

## 5. Product Scope for V1
### Must Have
- Create project/workspace
- Define domain profile
- Upload unstructured documents
- Extract candidate ontology concepts and relationships
- Review ontology suggestions
- Extract graph facts from documents
- Link facts to evidence spans
- Store graph in Neo4j (or equivalent)
- Export ontology + KG

### Should Have
- Domain term dictionary upload
- Synonym handling
- Entity resolution / deduplication
- Confidence scoring
- Approval workflow
- Graph visualization

### Could Have
- Natural-language question answering over graph + source text
- SHACL validation
- Embeddings-based similarity and concept clustering
- Multi-tenant team collaboration

---

## 6. Domain-Aware Design Principle
Because the user selected a **custom domain**, V1 should support a **domain profile** system rather than hardcoding one industry.

A **Domain Profile** contains:
- domain name
- terminology/glossary
- ontology seed classes
- allowed relation types
- attribute templates
- extraction hints/prompts
- normalization rules
- entity resolution rules
- document type templates

### Example Domain Profile Structure
```json
{
  "name": "Custom Domain",
  "description": "User-defined domain knowledge",
  "seed_classes": ["Concept", "Actor", "Event", "Asset", "Document"],
  "relation_types": ["relates_to", "part_of", "causes", "owned_by"],
  "synonyms": {
    "organization": ["company", "firm", "enterprise"]
  },
  "constraints": {
    "owned_by": {
      "domain": ["Asset"],
      "range": ["Actor"]
    }
  }
}
```

This makes the platform adaptable to any future vertical.

---

## 7. Key Use Cases
### Use Case 1: Generate Ontology from Documents
User uploads manuals, reports, standards, or internal documents.
System proposes:
- concepts/classes,
- subclass hierarchies,
- properties,
- relation types,
- synonyms and aliases.

### Use Case 2: Build KG from Unstructured Text
User uploads a document set.
System extracts:
- entities,
- relations,
- events,
- attributes,
- evidence passages,
then maps them to ontology schema and stores them in the graph.

### Use Case 3: Refine Ontology via Human Review
User reviews suggestions and accepts/rejects/edits:
- classes,
- properties,
- relation constraints,
- entity merges.

### Use Case 4: Trace Graph Facts to Evidence
For each triple or edge, user can view:
- source document,
- exact text span,
- extraction confidence,
- prompt/model provenance.

### Use Case 5: Export for Interoperability
User exports ontology and graph as:
- RDF/OWL,
- JSON-LD,
- GraphML,
- CSV node-edge tables.

---

## 8. Functional Requirements

## 8.1 Project & Workspace Management
- Create project
- Assign domain profile
- Upload files
- Organize sources by collection
- Track versions of ontology and KG

## 8.2 Document Ingestion
Input formats:
- PDF
- DOCX
- TXT
- Markdown
- CSV
- HTML

Pipeline:
- file upload
- text extraction
- cleaning
- chunking
- metadata capture
- language detection
- document type classification (optional)

## 8.3 Ontology Suggestion Engine
The system should generate candidate:
- classes
- subclasses
- object properties
- data properties
- aliases/synonyms
- cardinality hints
- relation constraints (domain/range)

Inputs:
- uploaded documents
- domain glossary
- existing ontology seeds
- user prompts/instructions

Outputs:
- proposed ontology graph
- confidence scores
- evidence snippets
- merge/duplicate suggestions

## 8.4 KG Extraction Engine
The system should extract:
- entities
- mentions
- entity types
- relations
- events
- attributes
- temporal facts
- source provenance

Every extracted fact should support:
- confidence
- extraction model info
- evidence span
- normalized entity ID
- ontology mapping

## 8.5 Entity Resolution / Canonicalization
System should detect when two mentions refer to the same entity using:
- string normalization
- domain synonyms
- embeddings similarity
- rule-based matching
- optional LLM-assisted disambiguation

## 8.6 Ontology Alignment
Map extracted entities and relations to ontology using:
- lexical match
- semantic similarity
- prompt-based classification
- ontology constraints
- user-approved mappings

## 8.7 Human Review Console
Users must be able to:
- approve/reject candidate classes
- rename concepts
- merge duplicates
- edit relation types
- fix entity mappings
- review source evidence
- compare ontology versions

## 8.8 Graph Visualization
Provide:
- node-edge explorer
- filters by entity type / source / confidence
- drill-down into source text
- schema view vs instance view

## 8.9 Export & Integration
Export formats:
- JSON
- JSON-LD
- RDF/Turtle
- OWL (basic)
- CSV nodes and edges

Integration targets (future):
- Neo4j
- Neptune
- GraphDB
- vector stores
- downstream RAG pipelines

---

## 9. Suggested V1 User Flow
### Flow A: New Project
1. User creates project
2. User selects or defines domain profile
3. User uploads documents
4. System preprocesses content
5. System generates ontology suggestions
6. User reviews and approves schema
7. System extracts KG instances aligned to ontology
8. User inspects graph and evidence
9. User exports results

### Flow B: Existing Ontology + New Documents
1. User imports ontology seeds
2. User uploads new documents
3. System extracts entities/relations under existing ontology
4. User reviews new candidates and graph growth

---

## 10. System Architecture (Python-first)

## 10.1 Recommended Stack
### Backend
- **FastAPI** for APIs
- **Pydantic** for schemas
- **SQLAlchemy** for relational metadata
- **Celery / RQ / FastAPI background tasks** for async jobs

### NLP / AI Layer
- spaCy for linguistic preprocessing
- sentence-transformers for embeddings
- LLM provider abstraction (OpenAI / Anthropic / local models)
- optional Hugging Face NER/relation models

### Storage
- **PostgreSQL** for project metadata, versions, review actions
- **Neo4j** for ontology + KG graph storage
- local filesystem / object storage for documents
- optional vector DB for semantic retrieval

### Frontend
- React or Next.js UI
- Cytoscape.js or React Flow for graph visualization
- simple admin/review dashboards

### Validation / Semantics
- RDFLib for RDF/OWL export
- pySHACL for constraint validation (optional in V1.5)

---

## 10.2 High-Level Architecture
```text
[Frontend UI]
    |
    v
[FastAPI API Layer]
    |
    +--> [Project / Auth / Config Service]
    +--> [Document Ingestion Service]
    +--> [Ontology Suggestion Service]
    +--> [KG Extraction Service]
    +--> [Review / Approval Service]
    +--> [Export Service]
    |
    +--> [PostgreSQL]
    +--> [Neo4j]
    +--> [Document Storage]
    +--> [LLM / Embedding Models]
```

---

## 11. Core Processing Pipeline
### Step 1: Ingest
- extract text from source files
- split into chunks
- store chunk metadata

### Step 2: Candidate Concept Mining
- noun phrase extraction
- domain term matching
- clustering similar terms
- LLM concept proposal
- rank concepts by frequency + relevance + semantic centrality

### Step 3: Ontology Drafting
- infer class hierarchy
- propose properties
- suggest domain/range
- detect synonyms
- build draft ontology

### Step 4: KG Extraction
- NER / mention detection
- relation extraction
- event extraction
- attribute extraction
- temporal expression parsing

### Step 5: Alignment
- map entity mentions to ontology classes
- map relations to ontology predicates
- validate constraints

### Step 6: Entity Resolution
- merge duplicate entities
- generate canonical IDs

### Step 7: Review
- present candidates to user
- collect approvals/edits
- update ontology/KG versions

### Step 8: Export / Query
- save graph
- export files
- provide graph browsing APIs

---

## 12. Data Model

## 12.1 Main Objects
### Project
- id
- name
- description
- domain_profile_id
- created_at

### DomainProfile
- id
- name
- description
- seed schema
- extraction rules
- synonym dictionary
- constraints

### SourceDocument
- id
- project_id
- filename
- type
- raw_text
- metadata
- checksum

### TextChunk
- id
- document_id
- chunk_index
- text
- offsets
- embedding_ref

### OntologyClass
- id
- project_id
- name
- label
- description
- parent_class_id
- status (candidate/approved/rejected)
- confidence

### OntologyProperty
- id
- project_id
- name
- property_type (object/data)
- domain_classes
- range_classes_or_datatype
- status
- confidence

### Entity
- id
- project_id
- canonical_name
- ontology_class_id
- aliases
- confidence

### Mention
- id
- entity_id
- chunk_id
- start_offset
- end_offset
- surface_form

### RelationInstance
- id
- subject_entity_id
- predicate_id
- object_entity_id_or_value
- chunk_id
- confidence
- extraction_method

### Evidence
- id
- relation_instance_id
- document_id
- chunk_id
- text_span
- start_offset
- end_offset

### ReviewAction
- id
- object_type
- object_id
- action
- user_comment
- timestamp

### Version
- id
- project_id
- version_type (ontology/kg)
- parent_version_id
- created_at
- notes

---

## 13. API Design (Draft)
### Project APIs
- `POST /projects`
- `GET /projects/{id}`
- `PATCH /projects/{id}`

### Domain Profile APIs
- `POST /domain-profiles`
- `GET /domain-profiles`
- `POST /projects/{id}/domain-profile`

### Document APIs
- `POST /projects/{id}/documents`
- `GET /projects/{id}/documents`
- `GET /documents/{id}`

### Ontology APIs
- `POST /projects/{id}/ontology/generate`
- `GET /projects/{id}/ontology/candidates`
- `POST /ontology/classes/{id}/approve`
- `POST /ontology/classes/{id}/reject`
- `POST /ontology/properties/{id}/approve`

### KG APIs
- `POST /projects/{id}/kg/extract`
- `GET /projects/{id}/entities`
- `GET /projects/{id}/relations`
- `GET /relations/{id}/evidence`

### Review APIs
- `POST /review/actions`
- `GET /projects/{id}/review/queue`

### Export APIs
- `GET /projects/{id}/export/jsonld`
- `GET /projects/{id}/export/rdf`
- `GET /projects/{id}/export/csv`

---

## 14. UI Modules
### 1. Project Dashboard
- project summary
- ingestion status
- ontology status
- extraction job status

### 2. Domain Setup Screen
- define domain name
- upload glossary
- add seed classes/relations
- configure rules

### 3. Document Ingestion Screen
- upload files
- parse preview
- classify documents

### 4. Ontology Review Studio
- class list
- hierarchy tree
- property editor
- merge suggestions
- evidence panel

### 5. KG Explorer
- graph view
- table view
- filters
- click edge → see evidence

### 6. Export & Versioning Screen
- download formats
- compare versions
- rollback/branch later

---

## 15. AI / NLP Strategy
Use a hybrid approach rather than pure LLM extraction.

### Rule-Based
Good for:
- exact domain terms
- document metadata
- deterministic mapping
- simple patterns

### Classical NLP
Good for:
- noun phrase extraction
- syntax-based relation candidates
- named entity baselines

### Embedding-Based
Good for:
- synonym clustering
- similarity matching
- ontology alignment
- duplicate detection

### LLM-Based
Good for:
- ontology class suggestion
- relation interpretation
- schema refinement
- ambiguous entity disambiguation
- natural-language explanation of extracted structure

### Recommendation
For V1, use a **hybrid pipeline**:
- rules + spaCy + embeddings + LLM verification

---

## 16. Quality & Trust Features
### Confidence Scoring
Every suggestion should include confidence from:
- extraction model confidence
- semantic similarity
- rule support
- ontology consistency checks

### Provenance
Store:
- source document
- chunk ID
- offsets
- extraction timestamp
- model/prompt version

### Explainability
For each candidate ontology concept or relation, show:
- why it was suggested
- supporting text snippets
- similar known concepts

---

## 17. Validation Rules
Basic validation for V1:
- duplicate class detection
- relation domain/range checks
- invalid self-loops (if restricted)
- missing entity type warnings
- orphan class warnings

Later:
- SHACL constraints
- OWL reasoning
- consistency validation against imported standards

---

## 18. Security & Enterprise Concerns
- role-based access control (later)
- audit log of review actions
- document-level access controls
- local/private model support for sensitive domains
- PII handling and redaction options

---

## 19. Success Metrics
### Product Metrics
- time to first draft ontology
- number of approved ontology suggestions
- KG precision after human review
- user correction rate
- ontology reuse across projects

### Technical Metrics
- extraction latency per document
- entity resolution precision
- relation extraction precision/recall
- export correctness

---

## 20. Recommended MVP Build Plan
### Phase 1: Foundation
- FastAPI app
- project/domain profile CRUD
- document upload and text extraction
- PostgreSQL metadata schema

### Phase 2: Ontology Drafting
- candidate term mining
- ontology class/property suggestion
- review endpoints

### Phase 3: KG Extraction
- entity + relation extraction
- evidence linkage
- Neo4j persistence

### Phase 4: Review + Visualization
- basic frontend
- graph viewer
- approval workflows

### Phase 5: Export + Versioning
- JSON-LD / CSV / RDF export
- ontology/KG version snapshots

---

## 21. Technical Risks
- hallucinated ontology classes from LLMs
- brittle relation extraction in ambiguous text
- entity resolution quality in domain-heavy corpora
- ontology overgrowth with too many low-quality classes
- difficult mapping between schema suggestions and instance extraction

### Mitigations
- human review required for ontology approval
- hybrid extraction pipeline
- confidence thresholds
- deduplication workflows
- domain profile constraints

---

## 22. Recommended Initial Repository Structure
```text
onto-app/
  backend/
    app/
      api/
      core/
      models/
      schemas/
      services/
        ingestion/
        ontology/
        extraction/
        alignment/
        review/
        export/
      db/
      workers/
    requirements.txt
  frontend/
    src/
      pages/
      components/
      features/
  docs/
    architecture.md
    ontology_kg_app_spec.md
```

---

## 23. Suggested V1 Architecture Decision
If we start implementation next, the best first milestone is:

**Milestone 1:**
- FastAPI backend
- project creation
- domain profile definition
- document upload
- text chunking
- ontology candidate generation endpoint

This gives the foundation for both ontology creation and KG extraction.

---

## 24. Open Questions
These should be finalized before coding deeper:
1. What is the first target domain?
2. Should ontology export follow OWL/RDF strictly or be app-native first?
3. Which LLM/model providers are acceptable?
4. Is graph DB required in V1, or can we start with relational + NetworkX?
5. Is human review mandatory before persistence?
6. Do we need multi-user collaboration from the start?

---

## 25. My Recommendation
Start with a **Python MVP** focused on:
- custom domain profile setup,
- ontology draft generation from uploaded text,
- KG extraction with provenance,
- Neo4j-backed storage,
- human review UI.

That gives a strong, domain-aware base and matches your goal of supporting **ontology + knowledge graph + unstructured text** together.
