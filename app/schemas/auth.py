import re

from pydantic import Field, field_validator

from app.core.roles import Role, normalize_role
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
    password: str = Field(min_length=6, max_length=128)
    role: str = Role.CASHIER.value
    phone: str | None = None

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("role")
    @classmethod
    def check_role(cls, value: str) -> str:
        return normalize_role(value)


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


class ForgotPasswordRequest(APIModel):
    email: str

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        return _validate_email(value)


class ResetPasswordRequest(APIModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=128)


class ChangePasswordRequest(APIModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)
