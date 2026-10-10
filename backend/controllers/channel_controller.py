import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session
from core.dependencies import AnyServerMember, CurrentUser, ServerAdmin, _ROLE_HIERARCHY
from models.server_member import MemberRole, ServerMember
from repositories.channel_repository import ChannelRepository
from repositories.server_member_repository import ServerMemberRepository
from repositories.user_repository import UserRepository
from schemas.channel import ChannelCreate, ChannelResponse, ChannelUpdate, VoiceParticipantResponse
from services.channel_service import ChannelService
from ws.connection_manager import manager

router = APIRouter(tags=["Channels"])


def get_channel_service(session: AsyncSession = Depends(get_session)) -> ChannelService:
    return ChannelService(ChannelRepository(session))


async def _require_role_via_channel(
    channel_id: uuid.UUID,
    minimum_role: MemberRole,
    current_user: CurrentUser,
    session: AsyncSession,
    service: ChannelService,
):
    """For endpoints with only channel_id in path: resolve server_id from channel, then check role."""
    channel = await service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    member = await ServerMemberRepository(session).get(current_user.id, channel.server_id)
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this server")
    if _ROLE_HIERARCHY[member.role] < _ROLE_HIERARCHY[minimum_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {minimum_role.value} role or higher",
        )
    return channel


# --- Endpoints with server_id in path ---

@router.get("/servers/{server_id}/channels", response_model=List[ChannelResponse])
async def list_channels(
    server_id: uuid.UUID,
    _member: AnyServerMember,
    service: ChannelService = Depends(get_channel_service),
):
    return await service.get_server_channels(server_id)


@router.post(
    "/servers/{server_id}/channels",
    response_model=ChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_channel(
    server_id: uuid.UUID,
    body: ChannelCreate,
    member: ServerAdmin,
    service: ChannelService = Depends(get_channel_service),
):
    return await service.create_channel(member.server_id, body)


# --- Endpoints with channel_id only ---

@router.get("/channels/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    service: ChannelService = Depends(get_channel_service),
):
    return await _require_role_via_channel(channel_id, MemberRole.MEMBER, current_user, session, service)


@router.get(
    "/channels/{channel_id}/voice/participants",
    response_model=List[VoiceParticipantResponse],
)
async def list_voice_participants(
    channel_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    service: ChannelService = Depends(get_channel_service),
):
    await _require_role_via_channel(channel_id, MemberRole.MEMBER, current_user, session, service)
    ids = manager.voice_peer_user_ids(channel_id)
    if not ids:
        return []
    users = await UserRepository(session).get_by_ids(ids)
    return [
        VoiceParticipantResponse(
            user_id=str(uid),
            username=users[uid].username if uid in users else "?",
        )
        for uid in ids
    ]


@router.patch("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: uuid.UUID,
    body: ChannelUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    service: ChannelService = Depends(get_channel_service),
):
    channel = await _require_role_via_channel(channel_id, MemberRole.ADMIN, current_user, session, service)
    return await service.update_channel(channel, body)


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: uuid.UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    service: ChannelService = Depends(get_channel_service),
):
    channel = await _require_role_via_channel(channel_id, MemberRole.ADMIN, current_user, session, service)
    await service.delete_channel(channel)
