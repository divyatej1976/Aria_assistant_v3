class AriaError(Exception):
    """Base error for expected application failures."""


class AuthorizationError(AriaError):
    """Raised when a learner cannot access a resource."""


class ValidationError(AriaError):
    """Raised when a domain invariant is violated."""
