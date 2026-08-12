from pydantic import BaseModel, Field


class ContextCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    goal_title: str | None = Field(default=None, max_length=200)
    configuration: dict = Field(default_factory=dict)


class ContextResponse(BaseModel):
    id: str
    title: str
    description: str | None
    status: str
    configuration: dict = Field(default_factory=dict)
