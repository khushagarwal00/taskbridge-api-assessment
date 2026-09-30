import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import app
from src.projects.controllers.project_controller import get_current_tenant_id


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    tenant = {"id": 1}

    def override_get_db():
        db = test_sessions()
        try:
            yield db
        finally:
            db.close()

    def override_tenant_id():
        return tenant["id"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_tenant_id] = override_tenant_id
    with TestClient(app) as client:
        yield client, tenant
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_project_crud_is_scoped_to_tenant(api_client):
    client, tenant = api_client
    created = client.post("/projects", json={"name": "Alpha"})
    assert created.status_code == 201
    project = created.json()
    assert project["team_id"] == 1
    assert project["status"] == "active"

    tenant["id"] = 2
    assert client.get("/projects").json() == []
    assert client.get(f"/projects/{project['id']}").status_code == 404
    assert client.patch(
        f"/projects/{project['id']}/status", json={"status": "complete"}
    ).status_code == 404
    assert client.delete(f"/projects/{project['id']}").status_code == 404

    tenant["id"] = 1
    assert client.patch(
        f"/projects/{project['id']}/status", json={"status": "complete"}
    ).json()["status"] == "complete"
    assert client.delete(f"/projects/{project['id']}").status_code == 204


def test_project_input_validation(api_client):
    client, _ = api_client
    assert client.post("/projects", json={"name": "   "}).status_code == 422
    assert client.post("/projects", json={"name": "A" * 201}).status_code == 422
    assert client.post("/projects", json={"name": "Valid", "team_id": 99}).status_code == 422


def test_project_routes_require_trusted_tenant_context(api_client):
    client, _ = api_client
    app.dependency_overrides.pop(get_current_tenant_id)
    assert client.get("/projects").status_code == 401