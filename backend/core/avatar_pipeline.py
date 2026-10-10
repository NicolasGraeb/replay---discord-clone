"""Upload awatara do MinIO (threadpool)."""

from __future__ import annotations

from core.avatar_image import render_avatar_upload
from core.media_s3 import put_chat_object


def process_and_store_avatar(raw: bytes, object_key: str) -> None:
    body, ctype = render_avatar_upload(raw)
    put_chat_object(object_key, body, ctype)
