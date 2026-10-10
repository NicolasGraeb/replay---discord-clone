import uuid
from typing import List

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from config.database import get_session
from config.envs import CHAT_IMAGE_MAX_UPLOAD_BYTES
from core.chat_image_pipeline import compress_and_store_chat_image
from core.dependencies import CurrentUser
from core.media_s3 import media_upload_configured
from models.channel import ChannelType
from repositories.channel_repository import ChannelRepository
from repositories.message_repository import MessageRepository
from schemas.message import (
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    message_realtime_payload,
    message_to_response,
)
from services.channel_service import ChannelService
from services.message_service import MessageService
from ws.connection_manager import manager

router = APIRouter(tags=["Messages"])


def get_message_service(session: AsyncSession = Depends(get_session)) -> MessageService:
    return MessageService(MessageRepository(session))


def get_channel_service(session: AsyncSession = Depends(get_session)) -> ChannelService:
    return ChannelService(ChannelRepository(session))


@router.post(
    "/channels/{channel_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    channel_id: uuid.UUID,
    body: MessageCreate,
    current_user: CurrentUser,
    message_service: MessageService = Depends(get_message_service),
    channel_service: ChannelService = Depends(get_channel_service),
):
    channel = await channel_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    msg = await message_service.send_message(current_user.id, channel_id, body)
    dto = message_to_response(msg)
    pl = message_realtime_payload(dto)
    await manager.broadcast(channel_id, pl)
    await manager.broadcast_voice_all(channel_id, pl)
    return dto


@router.post(
    "/channels/{channel_id}/messages/image",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message_image(
    channel_id: uuid.UUID,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    caption: str = Form(""),
    message_service: MessageService = Depends(get_message_service),
    channel_service: ChannelService = Depends(get_channel_service),
):
    if not media_upload_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload mediów wyłączony — ustaw MINIO_ENDPOINT i MINIO_BUCKET w .env",
        )
    channel = await channel_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    if channel.type != ChannelType.TEXT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Obrazki można wysyłać tylko na kanałach tekstowych",
        )
    ct = (file.content_type or "").lower()
    if not ct.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dozwolone są tylko pliki graficzne (image/*)",
        )
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pusty plik")
    if len(raw) > CHAT_IMAGE_MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plik za duży (max {CHAT_IMAGE_MAX_UPLOAD_BYTES // (1024 * 1024)} MB przed kompresją)",
        )
    cap = caption.strip()[:2000]
    object_key = f"messages/{channel_id}/{uuid.uuid4()}.webp"
    try:
        await run_in_threadpool(compress_and_store_chat_image, raw, object_key)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except ClientError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Błąd zapisu w magazynie: {e}",
        ) from e
    msg = await message_service.send_message_with_image(
        current_user.id,
        channel_id,
        cap,
        object_key,
    )
    dto = message_to_response(msg)
    await manager.broadcast(channel_id, message_realtime_payload(dto))
    return dto


@router.get("/channels/{channel_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    channel_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: MessageService = Depends(get_message_service),
):
    # Auth enforced at router level in app.py — no CurrentUser needed here
    rows = await service.get_channel_messages(channel_id, limit=limit, offset=offset)
    return [message_to_response(m) for m in rows]


@router.patch("/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: uuid.UUID,
    body: MessageUpdate,
    current_user: CurrentUser,
    service: MessageService = Depends(get_message_service),
):
    message = await service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    try:
        updated = await service.update_message(message, body, current_user.id)
        return message_to_response(updated)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: uuid.UUID,
    current_user: CurrentUser,
    service: MessageService = Depends(get_message_service),
):
    message = await service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    try:
        await service.delete_message(message, current_user.id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
