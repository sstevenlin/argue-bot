"""FastAPI web server for Argue Bot."""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(override=True)

from analyzer import argue_from_images, argue_from_text, result_to_dict
from llm import get_api_key
from vision import ImageInput

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
STATIC = PUBLIC / "static"

IS_VERCEL = bool(os.environ.get("VERCEL"))

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
            "error": "Anthropic API key not configured. Add ANTHROPIC_API_KEY to your .env file.",
        }


if not IS_VERCEL:

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(PUBLIC / "index.html")


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
            detail="Invalid Anthropic API key. Check your .env file.",
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


if not IS_VERCEL:
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("app:app", host="127.0.0.1", port=port, reload=True)


if __name__ == "__main__":
    main()
