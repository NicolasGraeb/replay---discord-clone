import uuid

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from config.database import get_session
from config.envs import AVATAR_MAX_UPLOAD_BYTES
from core.avatar_pipeline import process_and_store_avatar
from core.dependencies import CurrentUser
from core.media_s3 import delete_object_key, media_upload_configured
from repositories.user_repository import UserRepository
from schemas.user import UserCreate, UserResponse, UserUpdate, user_to_response
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session))


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, service: UserService = Depends(get_user_service)):
    try:
        u = await service.register(body)
        return user_to_response(u)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return user_to_response(current_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: uuid.UUID, service: UserService = Depends(get_user_service)):
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_to_response(user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
):
    try:
        u = await service.update(current_user, body)
        return user_to_response(u)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/me/avatar", response_model=UserResponse)
async def upload_my_avatar(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    service: UserService = Depends(get_user_service),
):
    if not media_upload_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload mediów wyłączony — ustaw MinIO w .env",
        )
    ct = (file.content_type or "").lower()
    if not ct.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dozwolone są tylko pliki graficzne",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pusty plik")
    if len(raw) > AVATAR_MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plik za duży (max {AVATAR_MAX_UPLOAD_BYTES // (1024 * 1024)} MB)",
        )
    key = f"avatars/{current_user.id}.webp"
    try:
        await run_in_threadpool(process_and_store_avatar, raw, key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Błąd zapisu: {e}",
        ) from e
    u = await service.set_avatar_key(current_user, key)
    return user_to_response(u)


@router.delete("/me/avatar", response_model=UserResponse)
async def delete_my_avatar(
    current_user: CurrentUser,
    service: UserService = Depends(get_user_service),
):
    prev = (current_user.avatar_url or "").strip()
    if prev and not prev.startswith(("http://", "https://")):
        await run_in_threadpool(delete_object_key, prev)
    u = await service.clear_avatar(current_user)
    return user_to_response(u)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(current_user: CurrentUser, service: UserService = Depends(get_user_service)):
    await service.delete(current_user)
