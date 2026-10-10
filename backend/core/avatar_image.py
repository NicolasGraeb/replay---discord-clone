"""Kwadratowy awatar (WebP) z dowolnego zdjęcia — crop środka + skala."""

from __future__ import annotations

import io
from typing import Tuple

from PIL import Image, ImageOps

_AVATAR_OUT = 256


def render_avatar_upload(raw: bytes) -> Tuple[bytes, str]:
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
        bg = Image.new("RGB", im.size, (24, 24, 24))
        bg.paste(im, mask=im.split()[3])
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")

    w, h = im.size
    side = min(w, h)
    left = max(0, (w - side) // 2)
    top = max(0, (h - side) // 2)
    im = im.crop((left, top, left + side, top + side))

    im = im.resize((_AVATAR_OUT, _AVATAR_OUT), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=72, method=6)
    body = buf.getvalue()
    if len(body) < 64:
        raise ValueError("Zbyt mały plik po przetworzeniu")
    return body, "image/webp"
