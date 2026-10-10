import json
import os
from typing import Annotated, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from config.envs import REFRESH_TOKEN_EXPIRE_DAYS
from repositories.refresh_token_repository import RefreshTokenRepository
from repositories.user_repository import UserRepository
from schemas.auth import TokenResponse
from schemas.user import UserLogin
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])

_REFRESH_COOKIE = "refresh_token"
_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
_COOKIE_SECURE = os.getenv("REFRESH_COOKIE_SECURE", "false").lower() in (
    "1",
    "true",
    "yes",
)


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(UserRepository(session), RefreshTokenRepository(session))


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=_COOKIE_SECURE,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    body: UserLogin,
    service: AuthService = Depends(get_auth_service),
):
    user = await service.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, refresh_token = await service.issue_tokens(user)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def _read_refresh_token(request: Request, refresh_cookie: Optional[str]) -> Optional[str]:
    if refresh_cookie:
        return refresh_cookie
    ct = request.headers.get("content-type", "")
    if "application/json" not in ct.lower():
        return None
    try:
        data = await request.json()
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(data, dict):
        t = data.get("refresh_token")
        return str(t) if t else None
    return None


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: Annotated[Optional[str], Cookie(alias=_REFRESH_COOKIE)] = None,
    service: AuthService = Depends(get_auth_service),
):
    raw = await _read_refresh_token(request, refresh_token)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    try:
        access_token, new_refresh_token = await service.rotate_tokens(raw)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    _set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    refresh_token: Annotated[Optional[str], Cookie(alias=_REFRESH_COOKIE)] = None,
    service: AuthService = Depends(get_auth_service),
):
    raw = await _read_refresh_token(request, refresh_token)
    if raw:
        await service.revoke_token(raw)
    response.delete_cookie(key=_REFRESH_COOKIE, path="/auth")
