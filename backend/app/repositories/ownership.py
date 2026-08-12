from uuid import UUID

from app.core.errors import AuthorizationError


def require_owner(*, requested_owner_id: UUID, authenticated_owner_id: UUID) -> None:
    """Enforce object-level ownership before any learner-owned read or write."""
    if requested_owner_id != authenticated_owner_id:
        raise AuthorizationError("The authenticated learner does not own this resource.")
