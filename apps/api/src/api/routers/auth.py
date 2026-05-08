"""Router de autenticación para acceso al frontend."""

import hmac

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.auth import create_access_token
from infrastructure.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    s = get_settings()
    valid_user = hmac.compare_digest(body.username, s.auth_user)
    valid_pass = hmac.compare_digest(body.password, s.auth_password)
    if not (valid_user and valid_pass):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return LoginResponse(
        access_token=create_access_token(username=body.username),
        username=body.username,
    )

