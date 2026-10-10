import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_session, get_session_factory
from core.security import decode_access_token
from models.channel import ChannelType
from repositories.channel_repository import ChannelRepository
from repositories.message_repository import MessageRepository
from repositories.user_repository import UserRepository
from schemas.message import MessageCreate, message_realtime_payload, message_to_response
from services.message_service import MessageService
from ws.connection_manager import manager

router = APIRouter()

_VOICE_ACTIONS = frozenset({"offer", "answer", "ice"})


@router.websocket("/ws/channels/{channel_id}")
async def channel_websocket(
    channel_id: uuid.UUID,
    websocket: WebSocket,
    token: str = Query(..., description="Valid access token"),
    session: AsyncSession = Depends(get_session),
):
    try:
        user_id = decode_access_token(token)
    except ValueError:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    user = await UserRepository(session).get_by_id(user_id)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    channel = await ChannelRepository(session).get_by_id(channel_id)
    if not channel:
        await websocket.close(code=4004, reason="Channel not found")
        return

    if channel.type == ChannelType.VOICE:
        await _run_voice_channel(channel_id, websocket, user.id, user.username)
        return

    await manager.connect(channel_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            content = str(data.get("content", "")).strip()
            if not content or len(content) > 4000:
                await websocket.send_json({"error": "Invalid message content"})
                continue

            async with get_session_factory()() as write_session:
                msg_repo = MessageRepository(write_session)
                message = await MessageService(msg_repo).send_message(
                    user_id, channel_id, MessageCreate(content=content)
                )
                dto = message_to_response(message)

            await manager.broadcast(channel_id, message_realtime_payload(dto))
    except WebSocketDisconnect:
        manager.disconnect(channel_id, websocket)


async def _run_voice_channel(
    channel_id: uuid.UUID,
    websocket: WebSocket,
    user_id: uuid.UUID,
    username: str,
) -> None:
    peer_ids = manager.voice_peer_user_ids(channel_id)
    await manager.connect_voice(channel_id, websocket, user_id)

    async with get_session_factory()() as read_session:
        users = await UserRepository(read_session).get_by_ids(peer_ids)
    peers_payload = [
        {"user_id": str(uid), "username": users[uid].username if uid in users else "?"}
        for uid in peer_ids
    ]

    try:
        await websocket.send_json(
            {"type": "voice_room", "event": "peers", "peers": peers_payload}
        )
        await manager.broadcast_voice_except(
            channel_id,
            websocket,
            {
                "type": "voice_room",
                "event": "peer_joined",
                "user_id": str(user_id),
                "username": username,
            },
        )

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "voice_signal":
                action = data.get("action")
                if action not in _VOICE_ACTIONS:
                    await websocket.send_json({"error": "Nieznana akcja voice_signal"})
                    continue
                to_raw = data.get("to")
                if not to_raw:
                    await websocket.send_json({"error": "Brak pola to"})
                    continue
                try:
                    target = uuid.UUID(str(to_raw))
                except (ValueError, TypeError):
                    await websocket.send_json({"error": "Nieprawidłowe to"})
                    continue
                if target == user_id:
                    await websocket.send_json({"error": "Nie wysyłaj sygnału do siebie"})
                    continue

                body = data.get("body")
                if body is None:
                    await websocket.send_json({"error": "Brak body"})
                    continue

                payload = {
                    "type": "voice_signal",
                    "from_user_id": str(user_id),
                    "action": action,
                    "body": body,
                }
                await manager.send_voice_to_user(channel_id, target, payload)
            elif "content" in data:
                content = str(data.get("content", "")).strip()
                if not content or len(content) > 4000:
                    await websocket.send_json({"error": "Invalid message content"})
                    continue
                async with get_session_factory()() as write_session:
                    msg_repo = MessageRepository(write_session)
                    message = await MessageService(msg_repo).send_message(
                        user_id, channel_id, MessageCreate(content=content)
                    )
                    dto = message_to_response(message)
                pl = message_realtime_payload(dto)
                await manager.broadcast_voice_all(channel_id, pl)
            else:
                await websocket.send_json(
                    {"error": "Oczekiwano voice_signal lub pola content"}
                )
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect_voice(channel_id, websocket)
        await manager.broadcast_voice_all(
            channel_id,
            {"type": "voice_room", "event": "peer_left", "user_id": str(user_id)},
        )
