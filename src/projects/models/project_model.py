from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_projects_name_nonempty"),
        CheckConstraint("length(trim(status)) > 0", name="ck_projects_status_nonempty"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")