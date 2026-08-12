from typing import Protocol
from uuid import UUID

from app.core.errors import AuthorizationError
from app.domain.entities import LearnerIdentity


class AuthProvider(Protocol):
    async def verify_access_token(self, token: str) -> LearnerIdentity:
        """Verify a token with the configured Supabase-compatible provider."""


class SupabaseAuthProvider:
    """Integration seam for Supabase Auth; verification is centralized here."""

    def __init__(self, *, jwt_secret: str | None) -> None:
        self.jwt_secret = jwt_secret

    async def verify_access_token(self, token: str) -> LearnerIdentity:
        if not token or not self.jwt_secret:
            raise AuthorizationError("Authentication provider is not configured.")
        raise NotImplementedError(
            "Supabase token verification is wired in the authentication phase."
        )


def assert_same_owner(*, owner_id: UUID, authenticated_user_id: UUID) -> None:
    if owner_id != authenticated_user_id:
        raise AuthorizationError("Cross-learner access is not permitted.")
