import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.business import PasswordResetToken, RevokedToken, User, utcnow
from app.schemas import auth as schema


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalars(select(User).where(func.lower(User.email) == email.lower())).first()


def signup(db: Session, payload: schema.SignupRequest) -> User:
    if get_user_by_email(db, payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        name=payload.name,
        email=payload.email,
        role=payload.role,
        phone=payload.phone,
        status="active",
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not active",
        )
    return user


def issue_token(user: User) -> str:
    return create_access_token(subject=user.id, extra_claims={"email": user.email, "role": user.role})


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def request_password_reset(db: Session, email: str) -> tuple[User, str] | None:
    """Create a reset token for the user if they exist and are active.

    Returns (user, plaintext_token) so the caller can email the link, or None
    if there is no matching active user (the endpoint stays generic either way).
    """
    user = get_user_by_email(db, email)
    if user is None or user.status != "active":
        return None

    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=utcnow() + timedelta(minutes=settings.password_reset_expire_minutes),
        used=False,
    )
    db.add(reset)
    db.commit()
    return user, token


def reset_password(db: Session, token: str, new_password: str) -> User | None:
    """Consume a valid reset token and set the user's new password."""
    reset = db.scalars(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_token(token))
    ).first()
    if reset is None or reset.used or reset.expires_at < utcnow():
        return None

    user = db.get(User, reset.user_id)
    if user is None:
        return None

    user.password_hash = hash_password(new_password)
    reset.used = True
    db.commit()
    db.refresh(user)
    return user


def revoke_token(db: Session, payload: dict) -> None:
    """Add the token's id to the denylist so it can no longer authenticate."""
    jti = payload.get("jti")
    if not jti:
        return

    # Opportunistically drop denylist rows whose tokens have already expired.
    db.query(RevokedToken).filter(RevokedToken.expires_at < utcnow()).delete()

    if db.scalar(select(RevokedToken).where(RevokedToken.jti == jti)) is None:
        exp = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None) if exp else utcnow()
        db.add(RevokedToken(jti=jti, expires_at=expires_at))
    db.commit()
