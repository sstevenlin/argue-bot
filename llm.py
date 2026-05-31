"""Anthropic Claude client helpers."""

from __future__ import annotations

import os

import anthropic


def get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if not key or key.startswith("sk-your"):
        raise EnvironmentError("Set ANTHROPIC_API_KEY as an environment variable.")
    return key


def client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_api_key())


def text_model(override: str | None = None) -> str:
    return override or os.environ.get("ARGUE_MODEL", "claude-sonnet-4-5")


def vision_model(override: str | None = None) -> str:
    return override or os.environ.get("ARGUE_VISION_MODEL", "claude-sonnet-4-5")


def extract_text(message: anthropic.types.Message) -> str:
    parts = [block.text for block in message.content if block.type == "text"]
    if not parts:
        raise RuntimeError("Model returned empty response.")
    return "".join(parts).strip()
