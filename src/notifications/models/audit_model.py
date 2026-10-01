from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class AuditEntry(Base):
	__tablename__ = "audit_entries"
	__table_args__ = (
		Index("ix_audit_entries_organization_timestamp", "organization_id", "timestamp"),
		Index(
			"ix_audit_entries_organization_project_timestamp",
			"organization_id",
			"project_id",
			"timestamp",
		),
	)

	id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
	event_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=False)
	project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
	event_type: Mapped[str] = mapped_column(String(100), nullable=False)
	actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
	organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
	old_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
	new_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
	timestamp: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		default=lambda: datetime.now(timezone.utc),
	)
