import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$")


def check_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise ValueError("A valid email address is required, like name@example.com")
    return normalized


def check_password(value: str) -> str:
    """New passwords: 8+ characters with a letter, a number and a symbol."""
    if not (re.search(r"[A-Za-z]", value) and re.search(r"\d", value) and re.search(r"[^A-Za-z0-9]", value)):
        raise ValueError("Password needs at least one letter, one number and one symbol")
    return value


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    device_label: str | None = Field(default=None, max_length=120)

    _email = field_validator("email")(classmethod(lambda cls, v: check_email(v)))
    _password = field_validator("password")(classmethod(lambda cls, v: check_password(v)))


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    device_label: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class SessionResponse(BaseModel):
    # None for cookie-only browser sessions (?bearer=false): no bearer copy
    # ever enters browser JS memory. API/native clients keep ?bearer=true.
    access_token: str | None = None
    token_type: str = "bearer"
    learner_id: str


class LearnerResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    verified: bool = False


class ProfileUpdateRequest(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    display_name: str | None = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return check_email(value)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
    _password = field_validator("new_password")(classmethod(lambda cls, v: check_password(v)))


class SessionRecord(BaseModel):
    id: str
    device_label: str | None
    is_current: bool
    created_at: datetime


class PasswordResetRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class PasswordResetConfirm(BaseModel):
    email: str
    token: str = Field(min_length=10, max_length=400)
    new_password: str = Field(min_length=8, max_length=128)
    _password = field_validator("new_password")(classmethod(lambda cls, v: check_password(v)))

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class EmailVerifyConfirm(BaseModel):
    email: str
    token: str = Field(min_length=10, max_length=400)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()
