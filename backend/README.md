# OntoForge Backend

A working FastAPI application for a domain-aware ontology generator and knowledge graph creator.

## Working features
- FastAPI app with modular routing
- SQLite + SQLAlchemy setup for app metadata and persistence
- Optional Neo4j integration for graph synchronization
- Domain profile CRUD
- Project CRUD
- Document upload and text extraction
- PDF parsing via `pypdf`
- DOCX parsing via `python-docx`
- Automatic KG extraction from uploaded documents
- Manual KG extraction endpoint for all project documents or a specific document
- Hybrid extraction pipeline with:
  - spaCy sentence/entity processing
  - optional transformer-assisted NER
  - optional LLM relation canonicalization
  - heuristic fallback patterns so the app still works without external models
- Ontology import from:
  - JSON app format
  - OWL / RDF XML
  - Turtle
  - N-Triples
  - N3
  - JSON-LD
- Ontology class/property persistence models
- KG entity/relation persistence models
- Evidence highlighting endpoint for extracted relations
- Editable ontology class/property APIs
- Editable relation APIs
- RDF / OWL / JSON-LD / Turtle export endpoints
- Built-in UI for ingestion, ontology building, KG exploration, evidence review, and export

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# optional: install transformer extras
# pip install -r requirements-ml.txt
uvicorn app.main:app --reload
```

Then open:
- App UI: `http://127.0.0.1:8000/ui`
- Root redirect: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Optional model configuration
Set these in `.env` if you want stronger extraction components:

```env
SPACY_MODEL=en_core_web_sm
ENABLE_TRANSFORMERS=false
TRANSFORMER_NER_MODEL=Jean-Baptiste/roberta-large-ner-english
LLM_API_URL=
LLM_API_KEY=
LLM_MODEL=
```

### Notes
- The app works without transformer or LLM configuration.
- If transformer support is desired, install `requirements-ml.txt` as well.
- For spaCy production quality, install the model explicitly:
  ```bash
  python -m spacy download en_core_web_sm
  ```

## Neo4j configuration
Neo4j is optional. If these environment variables are present, the app will create constraints and sync persisted ontology/KG records into Neo4j.

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
NEO4J_DATABASE=neo4j
```

If Neo4j is not configured, the relational persistence still works and graph sync endpoints return a disabled status.

## Main endpoints
### Core
- `GET /health`
- `GET /graph/health`

### Domain profiles and projects
- `POST /api/v1/domain-profiles`
- `GET /api/v1/domain-profiles`
- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`

### Documents
- `POST /api/v1/projects/{project_id}/documents?auto_extract=true`
- `GET /api/v1/projects/{project_id}/documents`

### Ontology
- `POST /api/v1/projects/{project_id}/ontology/generate`
- `POST /api/v1/projects/{project_id}/ontology/import`
- `POST /api/v1/projects/{project_id}/ontology/classes`
- `GET /api/v1/projects/{project_id}/ontology/classes`
- `PATCH /api/v1/projects/{project_id}/ontology/classes/{class_id}`
- `POST /api/v1/projects/{project_id}/ontology/properties`
- `GET /api/v1/projects/{project_id}/ontology/properties`
- `PATCH /api/v1/projects/{project_id}/ontology/properties/{property_id}`

### Knowledge graph
- `POST /api/v1/projects/{project_id}/kg/extract`
- `POST /api/v1/projects/{project_id}/kg/entities`
- `GET /api/v1/projects/{project_id}/kg/entities`
- `POST /api/v1/projects/{project_id}/kg/relations`
- `GET /api/v1/projects/{project_id}/kg/relations`
- `PATCH /api/v1/projects/{project_id}/kg/relations/{relation_id}`
- `GET /api/v1/projects/{project_id}/kg/relations/{relation_id}/evidence`
- `GET /api/v1/projects/{project_id}/graph/view`
- `POST /api/v1/projects/{project_id}/graph/sync`

### Export
- `GET /api/v1/projects/{project_id}/export/rdf`
- `GET /api/v1/projects/{project_id}/export/owl`
- `GET /api/v1/projects/{project_id}/export/jsonld`
- `GET /api/v1/projects/{project_id}/export/turtle`

## UI capabilities
The built-in UI includes:
- project creation and selection
- document upload with automatic KG extraction
- ontology upload/import in JSON or RDF/OWL formats
- ontology candidate generation from uploaded text
- ontology builder for classes and properties
- ontology tree view with edit actions
- KG builder for entities and relations
- relation editor
- evidence viewer with highlighted source snippet
- graph visualization using SVG
- manual KG extraction trigger for all uploaded documents
- RDF / OWL / JSON-LD / Turtle export buttons
- Neo4j sync action

## Ontology import formats
### 1. JSON app format
```json
{
  "classes": [
    {"name": "Person", "description": "An individual actor"},
    {"name": "Organization"},
    {"name": "Researcher", "parent": "Person"}
  ],
  "properties": [
    {"name": "works_for", "property_type": "object", "domain": "Person", "range": "Organization"},
    {"name": "email", "property_type": "data", "domain": "Person", "range_datatype": "string"}
  ]
}
```

### 2. RDF / OWL / Turtle
Supported formats:
- `.owl`
- `.rdf`
- `.xml`
- `.ttl`
- `.nt`
- `.n3`
- `.jsonld`

The importer maps common RDF/OWL constructs into the app model:
- `owl:Class`, `rdfs:Class`
- `rdfs:subClassOf`
- `owl:ObjectProperty`, `owl:DatatypeProperty`, `rdf:Property`
- `rdfs:domain`
- `rdfs:range`
- `rdfs:label`
- `rdfs:comment`

## KG extraction notes
The current extraction pipeline is an MVP hybrid implementation. It can:
- detect capitalized entity mentions
- use spaCy sentence parsing and NER when available
- optionally use transformer token classification if configured
- optionally use an LLM to canonicalize relation phrases to known predicates
- infer simple class assignments from phrases like `Alice is a Researcher`
- extract relation phrases like `works for`, `belongs to`, `located in`, `uses`, `owns`, `causes`
- extract simple data facts from patterns like `Alice has email alice@example.com`
- reuse imported ontology classes/properties when names align
- auto-create missing ontology properties as candidate predicates

## Persistence model summary
### SQL tables
- `projects`
- `source_documents`
- `ontology_classes`
- `ontology_properties`
- `entities`
- `relation_instances`

### Neo4j labels
- `Project`
- `OntologyClass`
- `OntologyProperty`
- `Entity`
- `RelationInstance`

## Smoke test status
The current application was smoke-tested with FastAPI `TestClient` for:
- project creation
- ontology class/property creation
- Turtle ontology import
- document upload with auto extraction
- manual KG extraction
- graph view retrieval
- relation evidence retrieval
- relation/class/property updates
- RDF / OWL / JSON-LD / Turtle exports

## Notes
- This is a working production-oriented baseline; deploy with managed secrets, migrations, and observability hardening for regulated environments.
- The ontology generation logic is intentionally lightweight and heuristic-based for now.
- The KG extraction logic mixes spaCy/optional ML with heuristics and should be upgraded further for production quality.
- Uploaded files are stored under `backend/data/uploads/`.
- SQLite DB is stored at `backend/data/app.db`.
- Neo4j sync is implemented and currently uses a reified `RelationInstance` node model.

## Enterprise modules added
- Auth/RBAC: `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/api-keys`, `/api/v1/users/me`, seeded Admin/Ontology Engineer/Data Analyst/Viewer/API User roles.
- Auditability: `audit_logs` model and admin audit-list endpoint.
- Operations: extraction job resource under `/api/v1/projects/{project_id}/jobs/extraction` with inline execution for local mode and Celery/RQ-ready persistence.
- Search/query: deterministic local search plus Neo4j Cypher execution support at `/api/v1/projects/{project_id}/search` and `/api/v1/projects/{project_id}/query`.
- Visualization: normalized graph/tree/timeline payload at `/api/v1/projects/{project_id}/visualization`.
- Versioning metadata: `ontology_versions` and `kg_metadata` tables for ontology/KG version tracking.

## Deployment assets
- Root `Dockerfile` runs the FastAPI API.
- Root `docker-compose.yml` starts API, PostgreSQL, Redis, Neo4j, and OpenSearch.
- `deploy/k8s/api-deployment.yaml` provides Kubernetes Deployment/Service manifests.
- `.github/workflows/ci.yml` installs dependencies, compiles the app, runs tests, and runs Ruff.

## Additional working ingestion and RBAC behavior
- `POST /api/v1/projects/{project_id}/documents/bulk` uploads multiple files in one request.
- `POST /api/v1/projects/{project_id}/documents/zip` expands a ZIP archive and ingests each file.
- `POST /api/v1/projects/{project_id}/documents/url` fetches and ingests a remote document URL.
- The extractor handles TXT/Markdown/HTML, CSV, JSON, XML, YAML, PDF, DOCX, XLSX, RTF, and RDF/OWL serializations.
- Set `REQUIRE_AUTH=true` to enforce JWT/API-key authentication and RBAC dependencies. When enabled, project creation requires `projects:write`, project reads require membership/admin access, and project member management requires owner/admin project role.
- `POST /api/v1/projects/{project_id}/query` executes SPARQL against the in-memory RDF graph generated from persisted project data; Cypher executes against Neo4j when configured.
