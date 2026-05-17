from fastapi import APIRouter

from app.api.routes import auth, documents, domain_profiles, export, graph, health, jobs, kg, ontology, projects, search, users, visualization
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(graph.router)

v1_router = APIRouter(prefix=settings.api_v1_prefix)
v1_router.include_router(auth.router)
v1_router.include_router(users.router)
v1_router.include_router(domain_profiles.router)
v1_router.include_router(projects.router)
v1_router.include_router(documents.router)
v1_router.include_router(ontology.router)
v1_router.include_router(kg.router)
v1_router.include_router(export.router)
v1_router.include_router(jobs.router)
v1_router.include_router(search.router)
v1_router.include_router(visualization.router)

api_router.include_router(v1_router)
