"""Vercel serverless entry point — self-contained FastAPI app."""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from analyzer import argue_from_images, argue_from_text, result_to_dict
from llm import get_api_key
from vision import ImageInput

app = FastAPI(title="Argue Bot", docs_url=None, redoc_url=None)

ALLOWED_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "application/octet-stream",
}

EXT_TO_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _resolve_mime(upload: UploadFile) -> str | None:
    content_type = (upload.content_type or "").split(";")[0].strip().lower()
    if content_type in ALLOWED_TYPES and content_type != "application/octet-stream":
        return content_type
    ext = Path(upload.filename or "").suffix.lower()
    return EXT_TO_MIME.get(ext)


@app.get("/api/health")
async def health():
    try:
        get_api_key()
        return {"ok": True}
    except EnvironmentError:
        return {
            "ok": False,
            "error": "Anthropic API key not configured.",
        }


@app.post("/api/analyze")
async def analyze(
    files: list[UploadFile] | None = File(default=None),
    text: str | None = Form(default=None),
):
    try:
        if text and text.strip():
            result = argue_from_text(text.strip())
        elif files:
            images: list[ImageInput] = []
            for upload in files:
                mime = _resolve_mime(upload)
                if not mime:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsupported file type: {upload.filename}. Use PNG, JPG, or WEBP.",
                    )
                data = await upload.read()
                if not data:
                    continue
                images.append(
                    ImageInput(
                        data=data,
                        mime=mime,
                        name=upload.filename or "screenshot",
                    )
                )
            if not images:
                raise HTTPException(status_code=400, detail="No valid images uploaded.")
            result = argue_from_images(images)
        else:
            raise HTTPException(
                status_code=400,
                detail="Upload screenshot(s) or paste a conversation transcript.",
            )

        return result_to_dict(result)

    except HTTPException:
        raise
    except EnvironmentError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except anthropic.AuthenticationError as e:
        raise HTTPException(
            status_code=500,
            detail="Invalid Anthropic API key.",
        ) from e
    except anthropic.RateLimitError as e:
        msg = "Claude rate limit hit. Wait a moment and try again."
        if "credit" in str(e).lower() or "balance" in str(e).lower():
            msg = (
                "Your Anthropic account is out of credits. "
                "Add billing at console.anthropic.com/settings/billing"
            )
        raise HTTPException(status_code=402, detail=msg) from e
    except anthropic.APIStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Claude API error: {e.message}",
        ) from e
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
