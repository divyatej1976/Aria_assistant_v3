from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Job:
    id: UUID
    kind: str
    owner_id: UUID
    status: str
    created_at: datetime

    @classmethod
    def pending(cls, *, kind: str, owner_id: UUID, created_at: datetime) -> "Job":
        return cls(
            id=uuid4(), kind=kind, owner_id=owner_id, status="PENDING", created_at=created_at
        )
