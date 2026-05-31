"""LLM-powered argument analysis and reply generation from screenshots."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from llm import client, extract_text, text_model, vision_model
from prompts import ANALYSIS_AND_RESPONSES
from vision import ImageInput, extract_conversation


@dataclass
class ArgueResult:
    conversation: str
    situation: str
    breakdown: str
    best_approach: str
    recommended_level: int
    responses: dict[int, str]


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def analyze_conversation(
    conversation: str,
    *,
    model: str | None = None,
) -> ArgueResult:
    response = client().messages.create(
        model=text_model(model),
        max_tokens=4096,
        temperature=0.7,
        system=ANALYSIS_AND_RESPONSES,
        messages=[
            {
                "role": "user",
                "content": f"Conversation transcript:\n\n{conversation}",
            }
        ],
    )
    raw = extract_text(response)
    data = _parse_json(raw)
    responses_raw = data.get("responses", {})
    responses = {int(k): v for k, v in responses_raw.items()}

    for level in range(1, 6):
        if level not in responses:
            raise RuntimeError(f"Model missing response level {level}.")

    return ArgueResult(
        conversation=conversation,
        situation=data.get("situation", ""),
        breakdown=data.get("breakdown", ""),
        best_approach=data.get("best_approach", ""),
        recommended_level=int(data.get("recommended_level", 3)),
        responses=responses,
    )


def argue_from_screenshots(
    image_paths: list[Path],
    *,
    vision_model: str | None = None,
    model: str | None = None,
) -> ArgueResult:
    return argue_from_images(
        image_paths,
        vision_model=vision_model,
        model=model,
    )


def argue_from_images(
    images: list[ImageInput] | list[Path],
    *,
    vision_model: str | None = None,
    model: str | None = None,
) -> ArgueResult:
    conversation = extract_conversation(
        images,
        model=vision_model,
    )
    return analyze_conversation(conversation, model=model)


def argue_from_text(
    conversation: str,
    *,
    model: str | None = None,
) -> ArgueResult:
    return analyze_conversation(conversation, model=model)


def result_to_dict(result: ArgueResult) -> dict:
    return {
        "conversation": result.conversation,
        "situation": result.situation,
        "breakdown": result.breakdown,
        "best_approach": result.best_approach,
        "recommended_level": result.recommended_level,
        "responses": {str(k): v for k, v in sorted(result.responses.items())},
    }


def result_to_json(result: ArgueResult) -> str:
    return json.dumps(result_to_dict(result), indent=2)
