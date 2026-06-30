from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.business import RevokedToken, User, utcnow
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
