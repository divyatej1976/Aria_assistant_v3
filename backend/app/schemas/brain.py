from typing import Literal

from pydantic import BaseModel


class ActionResponse(BaseModel):
    id: str
    capability: str
    status: Literal["proposed", "running", "done", "failed", "cancelled"]
    artifact_id: str | None = None
    error_code: str | None = None
    message: str
    auto_run: bool = True
