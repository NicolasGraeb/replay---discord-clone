import uuid
from typing import Dict, List, Set

from fastapi import WebSocket


class ConnectionManager:
    """In-process WebSocket hub. One instance per app (singleton via module)."""

    def __init__(self) -> None:
        self._channels: Dict[uuid.UUID, Set[WebSocket]] = {}
        self._voice: Dict[uuid.UUID, Dict[WebSocket, uuid.UUID]] = {}

    async def connect(self, channel_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._channels.setdefault(channel_id, set()).add(websocket)

    def disconnect(self, channel_id: uuid.UUID, websocket: WebSocket) -> None:
        sockets = self._channels.get(channel_id)
        if sockets:
            sockets.discard(websocket)
            if not sockets:
                del self._channels[channel_id]

    async def broadcast(self, channel_id: uuid.UUID, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._channels.get(channel_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel_id, ws)

    def active_count(self, channel_id: uuid.UUID) -> int:
        return len(self._channels.get(channel_id, set()))

    # --- Voice (WebRTC signaling) ---

    def voice_peer_user_ids(self, channel_id: uuid.UUID) -> List[uuid.UUID]:
        """Unikalne user_id już w pokoju (bez nowego gniazda)."""
        seen: List[uuid.UUID] = []
        for uid in self._voice.get(channel_id, {}).values():
            if uid not in seen:
                seen.append(uid)
        return seen

    async def connect_voice(
        self, channel_id: uuid.UUID, websocket: WebSocket, user_id: uuid.UUID
    ) -> None:
        await websocket.accept()
        self._voice.setdefault(channel_id, {})[websocket] = user_id

    def disconnect_voice(self, channel_id: uuid.UUID, websocket: WebSocket) -> None:
        room = self._voice.get(channel_id)
        if not room:
            return
        room.pop(websocket, None)
        if not room:
            del self._voice[channel_id]

    async def broadcast_voice_except(
        self, channel_id: uuid.UUID, except_ws: WebSocket, payload: dict
    ) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._voice.get(channel_id, {}).keys()):
            if ws is except_ws:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_voice(channel_id, ws)

    async def broadcast_voice_all(self, channel_id: uuid.UUID, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._voice.get(channel_id, {}).keys()):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_voice(channel_id, ws)

    async def send_voice_to_user(
        self, channel_id: uuid.UUID, target_user_id: uuid.UUID, payload: dict
    ) -> None:
        dead: list[WebSocket] = []
        for ws, uid in list(self._voice.get(channel_id, {}).items()):
            if uid != target_user_id:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect_voice(channel_id, ws)


manager = ConnectionManager()
