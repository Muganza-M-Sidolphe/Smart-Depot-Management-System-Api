from collections.abc import AsyncGenerator, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.roles import Role
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.business import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[Session, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise invalid

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise invalid

    subject = payload.get("sub")
    if subject is None:
        raise invalid

    user = db.get(User, int(subject)) if str(subject).isdigit() else None
    if user is None:
        raise invalid
    return user


def require_roles(*roles: Role | str) -> Callable[[User], User]:
    """Dependency factory: allow only the given roles, else respond 403."""
    allowed = {role.value if isinstance(role, Role) else str(role).lower() for role in roles}

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if (current_user.role or "").lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return checker
