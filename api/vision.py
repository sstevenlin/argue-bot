"""Read conversation text from iMessage screenshots."""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path

import anthropic

from llm import client, extract_text, vision_model
from prompts import EXTRACT_CONVERSATION

ANTHROPIC_MEDIA = {"image/jpeg", "image/png", "image/gif", "image/webp"}


@dataclass
class ImageInput:
    data: bytes
    mime: str = "image/png"
    name: str = "screenshot"


def _anthropic_media_type(mime: str) -> str:
    mime = mime.lower()
    if mime == "image/jpg":
        return "image/jpeg"
    if mime in ANTHROPIC_MEDIA:
        return mime
    raise ValueError(
        f"Unsupported image type ({mime}). Use PNG, JPG, or WEBP screenshots."
    )


def _image_block(data: bytes, mime: str) -> anthropic.types.ImageBlockParam:
    media_type = _anthropic_media_type(mime)
    encoded = base64.standard_b64encode(data).decode("ascii")
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": encoded,
        },
    }


def extract_conversation(
    images: list[ImageInput] | list[Path],
    *,
    model: str | None = None,
) -> str:
    if not images:
        raise ValueError("No screenshots provided.")

    content: list[anthropic.types.ContentBlockParam] = [
        {"type": "text", "text": EXTRACT_CONVERSATION}
    ]

    for item in images:
        if isinstance(item, Path):
            if not item.exists():
                raise FileNotFoundError(f"Screenshot not found: {item}")
            mime, _ = mimetypes.guess_type(item)
            content.append(_image_block(item.read_bytes(), mime or "image/png"))
        else:
            content.append(_image_block(item.data, item.mime))

    response = client().messages.create(
        model=vision_model(model),
        max_tokens=4096,
        temperature=0.1,
        messages=[{"role": "user", "content": content}],
    )
    return extract_text(response)
