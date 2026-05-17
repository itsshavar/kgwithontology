# OntoForge Architecture

OntoForge is organized as an API-first FastAPI backend with modular packages for authentication, ingestion, extraction, ontology management, knowledge graph persistence, Neo4j synchronization, search/query, visualization, and operational jobs.

## Runtime modes

- **Rule-based / deterministic:** default mode; uses text extraction, chunking, regex/NLP heuristics, RDFLib import/export, and local SQL persistence.
- **ML-assisted:** optional spaCy and transformer models can be enabled for richer NER and extraction.
- **LLM-assisted:** OpenAI-compatible endpoints can canonicalize relations and support future ontology suggestions.
- **Hybrid:** combines deterministic, ML, and LLM signals while preserving provenance and confidence scores.

## Storage

- PostgreSQL/SQLite: users, roles, permissions, projects, documents, ontology records, KG records, jobs, audit logs, API keys, version metadata.
- Neo4j: optional property graph sync over Bolt.
- OpenSearch/Elasticsearch: optional full-text and semantic search integration point.
- MinIO/S3: optional object storage integration point for large uploads.

## Enterprise capabilities

- JWT and API-key authentication.
- Built-in RBAC seed roles.
- Project membership model and audit log tables.
- Background extraction job resource, compatible with Celery/RQ workers.
- Docker Compose and Kubernetes deployment manifests.
- OpenAPI documentation at `/docs`.
