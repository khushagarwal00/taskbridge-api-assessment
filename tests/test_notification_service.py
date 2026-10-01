from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.database import Base
from src.notifications.models.audit_model import AuditEntry
from src.notifications.models.notification_model import Notification
from src.notifications.services.notification_service import NotificationService


@pytest.fixture
def db_session():
	engine = create_engine("sqlite://")
	Base.metadata.create_all(engine)
	with Session(engine) as session:
		yield session
	engine.dispose()


def test_notification_is_created_for_each_team_member(db_session):
	organization_id = uuid4()
	project_id = uuid4()
	recipients = ["member-1", "member-2", "member-3"]
	service = NotificationService(db_session)

	created = service.send_to_team_members(
		organization_id=organization_id,
		recipient_ids=recipients,
		project_id=project_id,
		message="Project status changed",
	)

	assert {notification.recipient_id for notification in created} == set(recipients)
	assert len(created) == len(recipients)
	assert all(notification.organization_id == organization_id for notification in created)
	assert all(notification.project_id == project_id for notification in created)
	assert all(notification.message == "Project status changed" for notification in created)


def test_notification_fanout_deduplicates_recipients(db_session):
	service = NotificationService(db_session)
	created = service.send_to_team_members(
		organization_id=uuid4(),
		recipient_ids=["member-1", "member-1", "member-2"],
		project_id=uuid4(),
		message="Project updated",
	)

	assert [notification.recipient_id for notification in created] == ["member-1", "member-2"]


def test_audit_record_is_created(db_session):
	organization_id = uuid4()
	project_id = uuid4()
	event_id = uuid4()
	timestamp = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
	service = NotificationService(db_session)

	entry = service.create_audit_entry(
		event_id=event_id,
		project_id=project_id,
		event_type="project.created",
		actor_id="user-1",
		organization_id=organization_id,
		old_state=None,
		new_state={"name": "Alpha", "status": "active"},
		timestamp=timestamp,
	)

	assert entry.event_id == event_id
	assert entry.project_id == project_id
	assert entry.organization_id == organization_id
	assert entry.actor_id == "user-1"
	assert entry.event_type == "project.created"
	assert entry.new_state == {"name": "Alpha", "status": "active"}
	assert db_session.scalar(select(AuditEntry).where(AuditEntry.event_id == event_id)) is not None


def test_audit_entry_is_immutable_on_duplicate_event(db_session):
	service = NotificationService(db_session)
	event_id = uuid4()
	organization_id = uuid4()
	original_project_id = uuid4()
	timestamp = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
	original = service.create_audit_entry(
		event_id=event_id,
		project_id=original_project_id,
		event_type="project.created",
		actor_id="user-1",
		organization_id=organization_id,
		old_state=None,
		new_state={"name": "Alpha"},
		timestamp=timestamp,
	)

	duplicate = service.create_audit_entry(
		event_id=event_id,
		project_id=uuid4(),
		event_type="project.deleted",
		actor_id="user-2",
		organization_id=organization_id,
		old_state={"name": "Alpha"},
		new_state=None,
		timestamp=datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc),
	)

	assert duplicate.id == original.id
	assert duplicate.project_id == original_project_id
	assert duplicate.event_type == "project.created"
	assert duplicate.actor_id == "user-1"
	assert duplicate.new_state == {"name": "Alpha"}
	assert duplicate.timestamp == timestamp.replace(tzinfo=None)
	assert len(db_session.scalars(select(AuditEntry)).all()) == 1


def test_audit_date_filter_returns_only_entries_in_range(db_session):
	service = NotificationService(db_session)
	organization_id = uuid4()
	project_id = uuid4()
	entries = [
		("event-before", datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc)),
		("event-start", datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)),
		("event-end", datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc)),
		("event-after", datetime(2026, 10, 2, 0, 1, tzinfo=timezone.utc)),
	]
	for event_suffix, timestamp in entries:
		service.create_audit_entry(
			event_id=uuid4(),
			project_id=project_id,
			event_type="project.status_changed",
			actor_id="user-1",
			organization_id=organization_id,
			old_state={"status": "active"},
			new_state={"status": "complete", "test_event": event_suffix},
			timestamp=timestamp,
		)

	filtered = service.list_audit_entries(
		organization_id=organization_id,
		project_id=project_id,
		from_timestamp=datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
		to_timestamp=datetime(2026, 10, 2, 0, 0, tzinfo=timezone.utc),
	)

	assert {entry.new_state["test_event"] for entry in filtered} == {"event-start", "event-end"}
	assert len(filtered) == 2


def test_notification_fanout_rejects_empty_message(db_session):
	with pytest.raises(ValueError, match="message must not be empty"):
		NotificationService(db_session).send_to_team_members(
			organization_id=uuid4(),
			recipient_ids=["member-1"],
			project_id=uuid4(),
			message="  ",
		)


def test_notification_fanout_rejects_empty_recipient_id(db_session):
	with pytest.raises(ValueError, match="recipient IDs must not be empty"):
		NotificationService(db_session).send_to_team_members(
			organization_id=uuid4(),
			recipient_ids=["member-1", " "],
			project_id=uuid4(),
			message="Project updated",
		)