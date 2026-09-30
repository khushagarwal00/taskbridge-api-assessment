from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.models.project_model import Project


class ProjectRepository:
	def __init__(self, db: Session) -> None:
		self.db = db

	def create(self, team_id: int, name: str, status: str) -> Project:
		project = Project(team_id=team_id, name=name, status=status)
		self.db.add(project)
		self.db.flush()
		return project

	def get_by_id(self, project_id: int, team_id: int) -> Project | None:
		return self.db.scalar(
			select(Project).where(
				Project.id == project_id,
				Project.team_id == team_id,
			)
		)

	def list_by_team(self, team_id: int, offset: int, limit: int) -> list[Project]:
		statement = (
			select(Project)
			.where(Project.team_id == team_id)
			.order_by(Project.id)
			.offset(offset)
			.limit(limit)
		)
		return list(self.db.scalars(statement).all())

	def update_status(self, project: Project, status: str) -> Project:
		project.status = status
		self.db.flush()
		return project

	def delete(self, project: Project) -> None:
		self.db.delete(project)
		self.db.flush()
