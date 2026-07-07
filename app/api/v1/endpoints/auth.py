from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_token_payload
from app.core.config import settings
from app.core.email import send_password_reset_email
from app.models.business import User
from app.schemas import auth as schema
from app.schemas.business import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schema.Token, status_code=status.HTTP_201_CREATED)
async def signup(payload: schema.SignupRequest, db: Session = Depends(get_db)) -> schema.Token:
    user = auth_service.signup(db, payload)
    return schema.Token(access_token=auth_service.issue_token(user), user=user)


@router.post("/login", response_model=schema.Token)
async def login(payload: schema.LoginRequest, db: Session = Depends(get_db)) -> schema.Token:
    user = auth_service.authenticate(db, payload.email, payload.password)
    return schema.Token(access_token=auth_service.issue_token(user), user=user)


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/forgot-password")
async def forgot_password(
    payload: schema.ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    result = auth_service.request_password_reset(db, payload.email)
    if result is not None:
        user, token = result
        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            user.name,
            reset_url,
            settings.password_reset_expire_minutes,
        )
    # Generic response either way, so we never reveal whether an email is registered.
    return {"detail": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    payload: schema.ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = auth_service.reset_password(db, payload.token, payload.new_password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return {"detail": "Your password has been reset. You can now log in."}


@router.post("/change-password")
async def change_password(
    payload: schema.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    ok = auth_service.change_password(db, current_user, payload.current_password, payload.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    return {"detail": "Your password has been changed."}


@router.post("/logout")
async def logout(
    payload: dict = Depends(get_token_payload),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    auth_service.revoke_token(db, payload)
    return {"detail": "Successfully logged out"}
