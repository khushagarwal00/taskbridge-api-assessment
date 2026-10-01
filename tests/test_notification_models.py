from datetime import timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database import Base
from src.notifications.models.audit_model import AuditEntry
from src.notifications.models.notification_model import Notification


def test_notification_and_audit_models_persist_with_uuid_ids():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    project_id = uuid4()
    organization_id = uuid4()
    event_id = uuid4()

    with Session(engine) as session:
        audit_entry = AuditEntry(
            event_id=event_id,
            project_id=project_id,
            event_type="project.created",
            actor_id="user-123",
            organization_id=organization_id,
            old_state=None,
            new_state={"name": "Migration", "status": "active"},
        )
        notification = Notification(
            organization_id=organization_id,
            recipient_id="user-123",
            project_id=project_id,
            message="Project Migration was created",
        )
        session.add_all([audit_entry, notification])
        session.commit()

        stored_audit_entry = session.scalar(
            select(AuditEntry).where(AuditEntry.event_id == event_id)
        )
        stored_notification = session.get(Notification, notification.id)

        assert stored_audit_entry is not None
        assert stored_audit_entry.project_id == project_id
        assert stored_audit_entry.new_state == {"name": "Migration", "status": "active"}
        assert stored_audit_entry.timestamp.tzinfo in (None, timezone.utc)
        assert stored_notification is not None
        assert stored_notification.organization_id == organization_id
        assert stored_notification.read is False
        assert stored_notification.created_at.tzinfo in (None, timezone.utc)

        session.add(
            AuditEntry(
                event_id=event_id,
                project_id=project_id,
                event_type="project.created",
                actor_id="user-123",
                organization_id=organization_id,
                old_state=None,
                new_state={"name": "Migration", "status": "active"},
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    engine.dispose()