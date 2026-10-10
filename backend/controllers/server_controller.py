import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from core.dependencies import (
    AnyServerMember,
    CurrentUser,
    ServerAdmin,
    ServerOwner,
)
from models.server_member import ServerMember
from repositories.channel_repository import ChannelRepository
from repositories.server_member_repository import ServerMemberRepository
from repositories.server_repository import ServerRepository
from repositories.user_repository import UserRepository
from schemas.server import (
    ServerCreate,
    ServerMemberResponse,
    ServerResponse,
    ServerUpdate,
    UpdateMemberRole,
)
from services.server_service import ServerService

router = APIRouter(prefix="/servers", tags=["Servers"])


def get_server_service(session: AsyncSession = Depends(get_session)) -> ServerService:
    return ServerService(
        ServerRepository(session),
        ServerMemberRepository(session),
        UserRepository(session),
        ChannelRepository(session),
    )


@router.get("", response_model=List[ServerResponse])
async def list_my_servers(
    current_user: CurrentUser,
    service: ServerService = Depends(get_server_service),
):
    return await service.list_my_servers(current_user)


@router.post("/", response_model=ServerResponse, status_code=status.HTTP_201_CREATED)
async def create_server(
    body: ServerCreate,
    current_user: CurrentUser,
    service: ServerService = Depends(get_server_service),
):
    return await service.create_server(current_user, body)


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: uuid.UUID,
    _member: AnyServerMember,
    service: ServerService = Depends(get_server_service),
):
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return server


@router.patch("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: uuid.UUID,
    body: ServerUpdate,
    _member: ServerAdmin,
    service: ServerService = Depends(get_server_service),
):
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return await service.update_server(server, body)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: uuid.UUID,
    _member: ServerOwner,
    service: ServerService = Depends(get_server_service),
):
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    await service.delete_server(server)


@router.get("/{server_id}/members", response_model=List[ServerMemberResponse])
async def get_members(
    server_id: uuid.UUID,
    _member: AnyServerMember,
    service: ServerService = Depends(get_server_service),
):
    return await service.get_member_rows(server_id)


@router.post(
    "/{server_id}/join",
    response_model=ServerMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def join_server(
    server_id: uuid.UUID,
    current_user: CurrentUser,
    service: ServerService = Depends(get_server_service),
):
    # User is not yet a member — cannot use require_server_role here
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    try:
        return await service.join_server(current_user, server)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{server_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_server(
    server_id: uuid.UUID,
    member: AnyServerMember,
    service: ServerService = Depends(get_server_service),
):
    server = await service.get_server(server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    try:
        await service.leave_server(member.user_id, server)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch(
    "/{server_id}/members/{target_user_id}/role",
    response_model=ServerMemberResponse,
)
async def update_member_role(
    server_id: uuid.UUID,
    target_user_id: uuid.UUID,
    body: UpdateMemberRole,
    _member: ServerOwner,
    service: ServerService = Depends(get_server_service),
):
    try:
        return await service.update_member_role(server_id, target_user_id, body.role)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
