from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.notifications.models.notification_schema import (
	AuditEntryCreate,
	AuditEntryRead,
	NotificationRead,
)
from src.notifications.services.notification_service import (
	NotificationNotFoundError,
	NotificationService,
)


router = APIRouter(tags=["notifications", "audit"])


def get_current_organization_id(request: Request) -> UUID:
	organization_id = getattr(request.state, "organization_id", None)
	if isinstance(organization_id, UUID):
		return organization_id
	if isinstance(organization_id, str):
		try:
			return UUID(organization_id)
		except ValueError:
			pass
	raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Authenticated organization context required",
	)


def get_current_user_id(request: Request) -> str:
	user_id = getattr(request.state, "user_id", None)
	if not isinstance(user_id, str) or not user_id.strip():
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Authenticated user context required",
		)
	return user_id


def require_audit_read_permission(request: Request) -> None:
	permissions = getattr(request.state, "permissions", ())
	if not isinstance(permissions, (set, frozenset, list, tuple)) or "audit:read" not in permissions:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Audit-read permission required",
		)


def get_notification_service(db: Annotated[Session, Depends(get_db)]) -> NotificationService:
	return NotificationService(db)


def require_audit_write_permission(request: Request) -> None:
	permissions = getattr(request.state, "permissions", ())
	if not isinstance(permissions, (set, frozenset, list, tuple)) or "audit:write" not in permissions:
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Audit-write permission required",
		)


def get_current_actor_id(request: Request) -> str:
	actor_id = getattr(request.state, "actor_id", None)
	if not isinstance(actor_id, str) or not actor_id.strip():
		actor_id = getattr(request.state, "user_id", None)
	if not isinstance(actor_id, str) or not actor_id.strip():
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Authenticated actor context required",
		)
	return actor_id


@router.post("/audit", response_model=AuditEntryRead, status_code=status.HTTP_201_CREATED)
def create_audit_entry(
	payload: AuditEntryCreate,
	organization_id: Annotated[UUID, Depends(get_current_organization_id)],
	actor_id: Annotated[str, Depends(get_current_actor_id)],
	service: Annotated[NotificationService, Depends(get_notification_service)],
	_: Annotated[None, Depends(require_audit_write_permission)],
) -> AuditEntryRead:
	try:
		entry = service.create_audit_entry(
			event_id=payload.event_id,
			project_id=payload.project_id,
			event_type=payload.event_type,
			actor_id=actor_id,
			organization_id=organization_id,
			old_state=payload.old_state,
			new_state=payload.new_state,
			timestamp=payload.timestamp,
		)
	except AuditEntryConflictError as exc:
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="Audit event conflicts with an existing event",
		) from exc
	return AuditEntryRead.model_validate(entry)


@router.get("/audit/{project_id}", response_model=list[AuditEntryRead])
def get_audit_history(
	project_id: Annotated[UUID, Path()],
	organization_id: Annotated[UUID, Depends(get_current_organization_id)],
	service: Annotated[NotificationService, Depends(get_notification_service)],
	_: Annotated[None, Depends(require_audit_read_permission)],
	offset: Annotated[int, Query(ge=0)] = 0,
	limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AuditEntryRead]:
	entries = service.list_audit_entries(
		organization_id=organization_id,
		offset=offset,
		limit=limit,
		project_id=project_id,
	)
	return [AuditEntryRead.model_validate(entry) for entry in entries]


@router.get("/notifications/{user_id}", response_model=list[NotificationRead])
def get_user_notifications(
	user_id: str,
	organization_id: Annotated[UUID, Depends(get_current_organization_id)],
	current_user_id: Annotated[str, Depends(get_current_user_id)],
	service: Annotated[NotificationService, Depends(get_notification_service)],
	unread_only: Annotated[bool, Query()] = False,
	offset: Annotated[int, Query(ge=0)] = 0,
	limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[NotificationRead]:
	if user_id != current_user_id:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notifications not found")
	notifications = service.list_notifications(
		organization_id=organization_id,
		recipient_id=current_user_id,
		offset=offset,
		limit=limit,
		unread_only=unread_only,
	)
	return [NotificationRead.model_validate(notification) for notification in notifications]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
	notification_id: Annotated[UUID, Path()],
	organization_id: Annotated[UUID, Depends(get_current_organization_id)],
	user_id: Annotated[str, Depends(get_current_user_id)],
	service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationRead:
	try:
		notification = service.mark_notification_read(notification_id, organization_id, user_id)
	except NotificationNotFoundError as exc:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Notification not found",
		) from exc
	return NotificationRead.model_validate(notification)