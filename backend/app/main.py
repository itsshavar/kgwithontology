from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.db.session import Base, engine
from app.models import (  # noqa: F401
    DomainProfile,
    KGEntity,
    OntologyClass,
    OntologyProperty,
    Project,
    RelationInstance,
    SourceDocument,
)
from app.services.graph.neo4j_service import neo4j_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.ui_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    try:
        neo4j_service.initialize_schema()
    except Exception as exc:  # pragma: no cover - runtime integration path
        print(f"Neo4j initialization warning: {exc}")

    yield

    neo4j_service.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    description="Domain-aware ontology generator and knowledge graph creator scaffold.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/ui", StaticFiles(directory=settings.ui_dir, html=True), name="ui")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui")


app.include_router(api_router)
