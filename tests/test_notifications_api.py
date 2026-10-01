from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database import Base, get_db
from src.main import app
from src.notifications.controllers.notification_controller import (
	get_current_actor_id,
	get_current_organization_id,
	get_current_user_id,
	require_audit_read_permission,
	require_audit_write_permission,
)
from src.notifications.models.audit_model import AuditEntry
from src.notifications.models.notification_model import Notification


@pytest.fixture
def notification_client():
	engine = create_engine(
		"sqlite://",
		connect_args={"check_same_thread": False},
		poolclass=StaticPool,
	)
	Base.metadata.create_all(engine)
	test_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
	organization_id = uuid4()
	other_organization_id = uuid4()
	user_id = "user-123"
	other_user_id = "user-456"

	def override_get_db():
		db = test_sessions()
		try:
			yield db
		finally:
			db.close()

	app.dependency_overrides[get_db] = override_get_db
	app.dependency_overrides[get_current_organization_id] = lambda: organization_id
	app.dependency_overrides[get_current_actor_id] = lambda: user_id
	app.dependency_overrides[get_current_user_id] = lambda: user_id
	app.dependency_overrides[require_audit_read_permission] = lambda: None
	app.dependency_overrides[require_audit_write_permission] = lambda: None
	with test_sessions.begin() as db:
		project_id = uuid4()
		event_id = uuid4()
		db.add_all(
			[
				AuditEntry(
					event_id=event_id,
					project_id=project_id,
					event_type="project.created",
					actor_id=user_id,
					organization_id=organization_id,
					old_state=None,
					new_state={"name": "Alpha", "status": "active"},
				),
				AuditEntry(
					event_id=uuid4(),
					project_id=uuid4(),
					event_type="project.deleted",
					actor_id=user_id,
					organization_id=other_organization_id,
					old_state={"name": "Hidden"},
					new_state=None,
				),
				Notification(
					organization_id=organization_id,
					recipient_id=user_id,
					project_id=project_id,
					message="Project Alpha was created",
				),
				Notification(
					organization_id=organization_id,
					recipient_id=other_user_id,
					project_id=project_id,
					message="Private notification",
				),
				Notification(
					organization_id=other_organization_id,
					recipient_id=user_id,
					project_id=uuid4(),
					message="Other organization notification",
				),
			]
		)
	with TestClient(app) as client:
		yield client, test_sessions, organization_id, user_id
	app.dependency_overrides.clear()
	Base.metadata.drop_all(engine)
	engine.dispose()


def test_create_audit_is_idempotent_and_history_is_project_scoped(notification_client):
	client, _, organization_id, user_id = notification_client
	project_id = uuid4()
	event_id = uuid4()
	payload = {
		"event_id": str(event_id),
		"project_id": str(project_id),
		"event_type": "project.status_changed",
		"old_state": {"status": "active"},
		"new_state": {"status": "complete"},
		"timestamp": "2026-10-01T12:00:00Z",
	}
	create_response = client.post("/audit", json=payload)
	duplicate_response = client.post("/audit", json=payload)

	assert create_response.status_code == 201
	assert duplicate_response.status_code == 201
	assert duplicate_response.json()["id"] == create_response.json()["id"]
	assert create_response.json()["actor_id"] == user_id
	assert create_response.json()["organization_id"] == str(organization_id)
	response = client.get(f"/audit/{project_id}")

	assert response.status_code == 200
	entries = response.json()
	assert len(entries) == 1
	assert entries[0]["organization_id"] == str(organization_id)
	assert entries[0]["event_type"] == "project.status_changed"


def test_notification_list_and_mark_read_are_recipient_scoped(notification_client):
	client, sessions, organization_id, user_id = notification_client
	response = client.get(f"/notifications/{user_id}", params={"unread_only": "true"})

	assert response.status_code == 200
	notifications = response.json()
	assert len(notifications) == 1
	assert notifications[0]["recipient_id"] == user_id
	assert notifications[0]["organization_id"] == str(organization_id)

	notification_id = notifications[0]["id"]
	assert client.patch(f"/notifications/{notification_id}/read").json()["read"] is True
	assert client.patch(f"/notifications/{notification_id}/read").json()["read"] is True
	assert client.get(f"/notifications/{user_id}", params={"unread_only": "true"}).json() == []
	assert client.get("/notifications/user-456").status_code == 404

	with sessions() as db:
		other_user_notification = db.query(Notification).filter_by(recipient_id="user-456").one()
	assert client.patch(f"/notifications/{other_user_notification.id}/read").status_code == 404


def test_audit_history_requires_audit_read_permission(notification_client):
	client, _, _, _ = notification_client
	app.dependency_overrides.pop(require_audit_read_permission)
	assert client.get(f"/audit/{uuid4()}").status_code == 403


def test_audit_creation_requires_audit_write_permission(notification_client):
	client, _, _, _ = notification_client
	app.dependency_overrides.pop(require_audit_write_permission)
	assert client.post("/audit", json={}).status_code == 403


def test_audit_entries_have_no_update_or_delete_endpoints(notification_client):
	client, _, _, _ = notification_client
	project_id = uuid4()

	assert client.put("/audit", json={}).status_code == 405
	assert client.delete("/audit").status_code == 405
	assert client.put(f"/audit/{project_id}", json={}).status_code == 405
	assert client.delete(f"/audit/{project_id}").status_code == 405