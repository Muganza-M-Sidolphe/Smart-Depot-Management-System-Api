import re

from pydantic import Field, field_validator

from app.schemas.business import APIModel, UserRead

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    value = value.strip()
    if not _EMAIL_RE.match(value):
        raise ValueError("Invalid email address")
    return value.lower()


class SignupRequest(APIModel):
    name: str = Field(min_length=1, max_length=120)
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: str = "staff"
    phone: str | None = None

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return _validate_email(value)


class LoginRequest(APIModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return _validate_email(value)


class Token(APIModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
