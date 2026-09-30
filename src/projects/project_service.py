from sqlalchemy import select
from sqlalchemy.orm import Session

from .project_model import Project


def create_project(
    db: Session,
    team_id: int,
    name: str,
    status: str,
) -> Project:
    project = Project(team_id=team_id, name=name, status=status)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project_status(
    db: Session,
    project_id: int,
    team_id: int,
    status: str,
) -> Project | None:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.team_id == team_id,
        )
    )
    if project is None:
        return None

    project.status = status
    db.commit()
    db.refresh(project)
    return project


def get_projects_by_team(db: Session, team_id: int) -> list[Project]:
    return list(
        db.scalars(
            select(Project)
            .where(Project.team_id == team_id)
            .order_by(Project.id)
        ).all()
    )


def delete_project(db: Session, project_id: int, team_id: int) -> bool:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.team_id == team_id,
        )
    )
    if project is None:
        return False

    db.delete(project)
    db.commit()
    return True