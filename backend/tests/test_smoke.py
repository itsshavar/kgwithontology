import os
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["REQUIRE_AUTH"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_auth_project_ingestion_ontology_kg_search_flow(tmp_path: Path):
    with TestClient(app) as client:
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": "admin@example.com", "username": "admin", "password": "super-secret", "full_name": "Admin User"},
        )
        assert registration.status_code == 201, registration.text

        login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "super-secret"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        roles = client.get("/api/v1/users/roles")
        assert roles.status_code == 200
        assert {role["name"] for role in roles.json()} >= {"Admin", "Viewer", "Data Analyst"}

        project = client.post("/api/v1/projects", json={"name": "Acme KG", "description": "Test workspace"}, headers=headers)
        assert project.status_code == 201, project.text
        project_id = project.json()["id"]

        upload = client.post(
            f"/api/v1/projects/{project_id}/documents?auto_extract=true",
            files={"file": ("sample.txt", b"Alice works for Acme Corp. Acme Corp is located in London.", "text/plain")},
        )
        assert upload.status_code == 201, upload.text
        assert upload.json()["document"]["chunk_count"] >= 1

        graph = client.get(f"/api/v1/projects/{project_id}/graph/view")
        assert graph.status_code == 200, graph.text
        assert "nodes" in graph.json()

        search = client.post(f"/api/v1/projects/{project_id}/search", json={"query": "Alice", "limit": 5})
        assert search.status_code == 200, search.text
        assert search.json()["hits"]


        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as archive:
            archive.writestr("structured.csv", "name,relation,target\nAlice,uses,OntoForge")
        zip_upload = client.post(
            f"/api/v1/projects/{project_id}/documents/zip?auto_extract=false",
            files={"file": ("bundle.zip", zip_buffer.getvalue(), "application/zip")},
        )
        assert zip_upload.status_code == 201, zip_upload.text
        assert zip_upload.json()[0]["document"]["filename"] == "structured.csv"

        sparql = client.post(
            f"/api/v1/projects/{project_id}/query",
            json={"language": "sparql", "query": "SELECT ?s WHERE { ?s ?p ?o }", "limit": 5},
        )
        assert sparql.status_code == 200, sparql.text
        assert sparql.json()["executed"] is True

        viz = client.get(f"/api/v1/projects/{project_id}/visualization")
        assert viz.status_code == 200, viz.text
        assert set(viz.json()) == {"nodes", "edges", "ontology_tree", "timeline"}

        api_key = client.post("/api/v1/auth/api-keys", json={"name": "ci"}, headers=headers)
        assert api_key.status_code == 201, api_key.text
        me = client.get("/api/v1/users/me", headers={"X-API-Key": api_key.json()["api_key"]})
        assert me.status_code == 200, me.text
        assert me.json()["username"] == "admin"
