from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.notifications.models.audit_model import AuditEntry
from src.notifications.models.notification_model import Notification
from src.notifications.repositories.notification_repository import NotificationRepository


class NotificationNotFoundError(LookupError):
	pass


class AuditEntryConflictError(LookupError):
	pass


class NotificationService:
	def __init__(self, db: Session) -> None:
		self.db = db
		self.repository = NotificationRepository(db)

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
		try:
			with self.db.begin():
				entry = self.repository.get_audit_entry_by_event_id(event_id)
				if entry is not None:
					if entry.organization_id != organization_id:
						raise AuditEntryConflictError
					return entry
				return self.repository.create_audit_entry(
					event_id,
					project_id,
					event_type,
					actor_id,
					organization_id,
					old_state,
					new_state,
					timestamp,
				)
		except IntegrityError as exc:
			self.db.rollback()
			entry = self.repository.get_audit_entry_by_event_id(event_id)
			if entry is not None and entry.organization_id == organization_id:
				return entry
			raise AuditEntryConflictError from exc

	def list_audit_entries(
		self,
		organization_id: UUID,
		offset: int = 0,
		limit: int = 50,
		project_id: UUID | None = None,
		event_type: str | None = None,
		from_timestamp: datetime | None = None,
		to_timestamp: datetime | None = None,
	) -> list[AuditEntry]:
		return self.repository.list_audit_entries(
			organization_id,
			offset,
			limit,
			project_id,
			event_type,
			from_timestamp,
			to_timestamp,
		)

	def list_notifications(
		self,
		organization_id: UUID,
		recipient_id: str,
		offset: int = 0,
		limit: int = 50,
		unread_only: bool = False,
	) -> list[Notification]:
		return self.repository.list_notifications(
			organization_id,
			recipient_id,
			offset,
			limit,
			unread_only,
		)

	def send_to_team_members(
		self,
		organization_id: UUID,
		recipient_ids: list[str],
		project_id: UUID,
		message: str,
	) -> list[Notification]:
		if not message.strip():
			raise ValueError("message must not be empty")
		if any(not recipient_id.strip() for recipient_id in recipient_ids):
			raise ValueError("recipient IDs must not be empty")
		unique_recipient_ids = list(dict.fromkeys(recipient_ids))
		with self.db.begin():
			return self.repository.create_notifications(
				organization_id,
				unique_recipient_ids,
				project_id,
				message,
			)

	def mark_notification_read(
		self,
		notification_id: UUID,
		organization_id: UUID,
		recipient_id: str,
	) -> Notification:
		with self.db.begin():
			notification = self.repository.get_notification(
				notification_id,
				organization_id,
				recipient_id,
			)
			if notification is None:
				raise NotificationNotFoundError
			notification.read = True
			self.db.flush()
		return notification