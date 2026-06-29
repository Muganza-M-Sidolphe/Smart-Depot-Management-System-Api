from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
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
