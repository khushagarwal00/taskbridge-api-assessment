from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    status: str = Field(default="active", min_length=1, max_length=50)

    @field_validator("name", "status", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProjectStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1, max_length=50)

    @field_validator("status", mode="before")
    @classmethod
    def strip_status(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    name: str
    status: str