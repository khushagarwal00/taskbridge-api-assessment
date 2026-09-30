from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.projects.models.project_schema import ProjectCreate, ProjectRead, ProjectStatusUpdate
from src.projects.services.project_service import ProjectNotFoundError, ProjectService


router = APIRouter(prefix="/projects", tags=["projects"])


def get_current_tenant_id(request: Request) -> int:
	"""Read tenant identity set by trusted authentication middleware."""
	team_id = getattr(request.state, "tenant_id", None)
	if isinstance(team_id, bool) or not isinstance(team_id, int) or team_id <= 0:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Authenticated tenant context required",
		)
	return team_id


def get_project_service(db: Annotated[Session, Depends(get_db)]) -> ProjectService:
	return ProjectService(db)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
	payload: ProjectCreate,
	team_id: Annotated[int, Depends(get_current_tenant_id)],
	service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectRead:
	project = service.create_project(team_id, payload.name, payload.status)
	return ProjectRead.model_validate(project)


@router.get("", response_model=list[ProjectRead])
def list_projects(
	team_id: Annotated[int, Depends(get_current_tenant_id)],
	service: Annotated[ProjectService, Depends(get_project_service)],
	offset: Annotated[int, Query(ge=0)] = 0,
	limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ProjectRead]:
	projects = service.list_projects(team_id, offset, limit)
	return [ProjectRead.model_validate(project) for project in projects]


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
	project_id: Annotated[int, Path(gt=0)],
	team_id: Annotated[int, Depends(get_current_tenant_id)],
	service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectRead:
	try:
		project = service.get_project(project_id, team_id)
	except ProjectNotFoundError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
	return ProjectRead.model_validate(project)


@router.patch("/{project_id}/status", response_model=ProjectRead)
def update_project_status(
	payload: ProjectStatusUpdate,
	project_id: Annotated[int, Path(gt=0)],
	team_id: Annotated[int, Depends(get_current_tenant_id)],
	service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectRead:
	try:
		project = service.update_project_status(project_id, team_id, payload.status)
	except ProjectNotFoundError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
	return ProjectRead.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
	project_id: Annotated[int, Path(gt=0)],
	team_id: Annotated[int, Depends(get_current_tenant_id)],
	service: Annotated[ProjectService, Depends(get_project_service)],
) -> Response:
	try:
		service.delete_project(project_id, team_id)
	except ProjectNotFoundError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found") from exc
	return Response(status_code=status.HTTP_204_NO_CONTENT)
