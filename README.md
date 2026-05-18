# OntoForge Knowledge Graph & Ontology Builder

OntoForge is a Python 3.11+ FastAPI platform for document ingestion, ontology creation, knowledge graph extraction, semantic export, Neo4j synchronization, RBAC-protected collaboration, and graph visualization.

## Highlights

- Modular FastAPI backend with versioned REST APIs and Swagger UI.
- Upload and process single files, bulk uploads, ZIP archives, remote URLs, text, PDF, DOCX, XLSX, CSV/JSON/XML/YAML, markup, and semantic-web formats.
- Generate entities, relations, RDF triples, ontology classes, and ontology properties.
- Import/export TTL, OWL/RDF XML, JSON-LD, N-Triples, N3, and application JSON.
- Works without LLMs via deterministic rule/NLP pipelines; optional LLM provider hooks are available.
- JWT login, API keys, built-in RBAC roles, project memberships, and audit logs.
- Optional Neo4j sync and Cypher query execution.
- Built-in web UI for ingestion, ontology editing, KG exploration, evidence review, visualization, and export.
- Docker Compose, Kubernetes manifests, GitHub Actions CI, and pytest smoke coverage for end-to-end workflows.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- UI: <http://127.0.0.1:8000/ui>
- Swagger/OpenAPI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/health>

## Docker Compose

```bash
docker compose up --build
```

This starts the API, PostgreSQL, Redis, Neo4j, and OpenSearch for an enterprise-style local environment.

## Core API areas

- `/api/v1/auth/*` — registration, login, API keys.
- `/api/v1/users/*` — profile, roles, admin user/audit views.
- `/api/v1/projects/*` — workspaces, documents, ontology, KG, jobs, search, query, visualization, export, Neo4j sync.
- `/health` and `/graph/health` — platform and Neo4j health checks.

See `backend/README.md` and `docs/architecture.md` for implementation details.
