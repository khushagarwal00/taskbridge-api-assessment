from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuditEntryCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	event_id: UUID
	project_id: UUID
	event_type: str = Field(min_length=1, max_length=100)
	old_state: dict[str, Any] | None = None
	new_state: dict[str, Any] | None = None
	timestamp: datetime

	@field_validator("timestamp")
	@classmethod
	def require_timezone(cls, value: datetime) -> datetime:
		if value.utcoffset() is None:
			raise ValueError("timestamp must include a timezone")
		return value


class AuditEntryRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	project_id: UUID
	event_type: str
	actor_id: str
	organization_id: UUID
	old_state: dict[str, Any] | None
	new_state: dict[str, Any] | None
	timestamp: datetime


class NotificationRead(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: UUID
	organization_id: UUID
	recipient_id: str
	project_id: UUID
	message: str
	read: bool
	created_at: datetime