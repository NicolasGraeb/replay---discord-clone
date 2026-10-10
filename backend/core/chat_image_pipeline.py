"""Kompresja + upload obrazka czatu (wywoływane z threadpool)."""

from __future__ import annotations

from core.image_process import render_chat_image
from core.media_s3 import put_chat_object


def compress_and_store_chat_image(raw: bytes, object_key: str) -> None:
    body, ctype = render_chat_image(raw)
    put_chat_object(object_key, body, ctype)
