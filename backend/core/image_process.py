"""Kompresja obrazów do czatu (max krawędź, WebP, bez EXIF)."""

from __future__ import annotations

import io
from typing import Tuple

from PIL import Image, ImageOps

from config.envs import IMAGE_MAX_EDGE


def render_chat_image(raw: bytes) -> Tuple[bytes, str]:
    """
    Otwiera obraz, prostuje EXIF, skaluje do IMAGE_MAX_EDGE, zapisuje WebP.
    Zwraca (bytes, content_type).
    """
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except OSError as e:
        raise ValueError("Nieprawidłowy plik graficzny") from e

    im = ImageOps.exif_transpose(im)

    if getattr(im, "is_animated", False):
        im.seek(0)

    if im.mode == "P":
        im = im.convert("RGBA")
    if im.mode == "RGBA":
        bg = Image.new("RGB", im.size, (18, 18, 18))
        bg.paste(im, mask=im.split()[3])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")

    w, h = im.size
    edge = max(w, h)
    max_edge = max(320, min(IMAGE_MAX_EDGE, 8192))
    if edge > max_edge:
        scale = max_edge / float(edge)
        nw = max(1, int(w * scale))
        nh = max(1, int(h * scale))
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    im.save(
        buf,
        format="WEBP",
        quality=82,
        method=6,
        lossless=False,
    )
    body = buf.getvalue()
    if len(body) < 256:
        raise ValueError("Obraz po kompresji jest zbyt mały — prawdopodobnie uszkodzony plik")
    return body, "image/webp"
