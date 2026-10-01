from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.notifications.models.audit_model import AuditEntry
from src.notifications.models.notification_model import Notification


class NotificationRepository:
	def __init__(self, db: Session) -> None:
		self.db = db

	def get_audit_entry_by_event_id(self, event_id: UUID) -> AuditEntry | None:
		return self.db.scalar(select(AuditEntry).where(AuditEntry.event_id == event_id))

	def create_audit_entry(
		self,
		event_id: UUID,
		project_id: UUID,
		event_type: str,
		actor_id: str,
		organization_id: UUID,
		old_state: dict[str, Any] | None,
		new_state: dict[str, Any] | None,
		timestamp: datetime,
	) -> AuditEntry:
		entry = AuditEntry(
			event_id=event_id,
			project_id=project_id,
			event_type=event_type,
			actor_id=actor_id,
			organization_id=organization_id,
			old_state=old_state,
			new_state=new_state,
			timestamp=timestamp,
		)
		self.db.add(entry)
		self.db.flush()
		return entry

	def list_audit_entries(
		self,
		organization_id: UUID,
		offset: int,
		limit: int,
		project_id: UUID | None = None,
		event_type: str | None = None,
		from_timestamp: datetime | None = None,
		to_timestamp: datetime | None = None,
	) -> list[AuditEntry]:
		statement = select(AuditEntry).where(AuditEntry.organization_id == organization_id)
		if project_id is not None:
			statement = statement.where(AuditEntry.project_id == project_id)
		if event_type is not None:
			statement = statement.where(AuditEntry.event_type == event_type)
		if from_timestamp is not None:
			statement = statement.where(AuditEntry.timestamp >= from_timestamp)
		if to_timestamp is not None:
			statement = statement.where(AuditEntry.timestamp <= to_timestamp)
		statement = (
			statement.order_by(AuditEntry.timestamp.desc(), AuditEntry.id.desc())
			.offset(offset)
			.limit(limit)
		)
		return list(self.db.scalars(statement).all())

	def list_notifications(
		self,
		organization_id: UUID,
		recipient_id: str,
		offset: int,
		limit: int,
		unread_only: bool,
	) -> list[Notification]:
		statement = select(Notification).where(
			Notification.organization_id == organization_id,
			Notification.recipient_id == recipient_id,
		)
		if unread_only:
			statement = statement.where(Notification.read.is_(False))
		statement = (
			statement.order_by(Notification.created_at.desc(), Notification.id.desc())
			.offset(offset)
			.limit(limit)
		)
		return list(self.db.scalars(statement).all())

	def get_notification(
		self,
		notification_id: UUID,
		organization_id: UUID,
		recipient_id: str,
	) -> Notification | None:
		return self.db.scalar(
			select(Notification).where(
				Notification.id == notification_id,
				Notification.organization_id == organization_id,
				Notification.recipient_id == recipient_id,
			)
		)