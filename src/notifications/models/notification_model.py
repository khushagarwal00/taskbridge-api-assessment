from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Index, String, Text, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Notification(Base):
	__tablename__ = "notifications"
	__table_args__ = (
		Index(
			"ix_notifications_organization_recipient_created",
			"organization_id",
			"recipient_id",
			"created_at",
		),
		Index("ix_notifications_project", "project_id"),
	)

	id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
	organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
	recipient_id: Mapped[str] = mapped_column(String(255), nullable=False)
	project_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
	message: Mapped[str] = mapped_column(Text, nullable=False)
	read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		default=lambda: datetime.now(timezone.utc),
	)
