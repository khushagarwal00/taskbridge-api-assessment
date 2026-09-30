from sqlalchemy.orm import Session

from src.projects.models.project_model import Project
from src.projects.repositories.project_repository import ProjectRepository


class ProjectNotFoundError(LookupError):
    pass


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = ProjectRepository(db)

    @staticmethod
    def _validate_tenant(team_id: int) -> None:
        if isinstance(team_id, bool) or team_id <= 0:
            raise ValueError("team_id must be a positive integer")

    @staticmethod
    def _validate_text(value: str, field: str, max_length: int) -> str:
        if not isinstance(value, str):
            raise ValueError(f"{field} must be a string")
        normalized = value.strip()
        if not normalized or len(normalized) > max_length:
            raise ValueError(f"{field} must contain 1 to {max_length} characters")
        return normalized

    def create_project(self, team_id: int, name: str, status: str = "active") -> Project:
        self._validate_tenant(team_id)
        name = self._validate_text(name, "name", 200)
        status = self._validate_text(status, "status", 50)
        with self.db.begin():
            return self.repository.create(team_id, name, status)

    def get_project(self, project_id: int, team_id: int) -> Project:
        self._validate_tenant(team_id)
        if isinstance(project_id, bool) or project_id <= 0:
            raise ValueError("project_id must be a positive integer")
        project = self.repository.get_by_id(project_id, team_id)
        if project is None:
            raise ProjectNotFoundError
        return project

    def list_projects(self, team_id: int, offset: int = 0, limit: int = 50) -> list[Project]:
        self._validate_tenant(team_id)
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("offset must be non-negative and limit must be between 1 and 100")
        return self.repository.list_by_team(team_id, offset, limit)

    def update_project_status(self, project_id: int, team_id: int, status: str) -> Project:
        self._validate_tenant(team_id)
        if isinstance(project_id, bool) or project_id <= 0:
            raise ValueError("project_id must be a positive integer")
        status = self._validate_text(status, "status", 50)
        with self.db.begin():
            project = self.repository.get_by_id(project_id, team_id)
            if project is None:
                raise ProjectNotFoundError
            return self.repository.update_status(project, status)

    def delete_project(self, project_id: int, team_id: int) -> None:
        self._validate_tenant(team_id)
        if isinstance(project_id, bool) or project_id <= 0:
            raise ValueError("project_id must be a positive integer")
        with self.db.begin():
            project = self.repository.get_by_id(project_id, team_id)
            if project is None:
                raise ProjectNotFoundError
            self.repository.delete(project)