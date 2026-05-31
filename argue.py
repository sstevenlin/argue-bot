#!/usr/bin/env python3
"""Argue Bot — screenshot-based iMessage rebuttal generator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)

from analyzer import argue_from_screenshots, argue_from_text, result_to_json


def copy_to_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def _print_result(result, *, pick: int | None) -> None:
    print("\n--- conversation ---")
    print(result.conversation)

    print("\n--- situation ---")
    print(result.situation)

    print("\n--- breakdown ---")
    print(result.breakdown)

    print("\n--- best approach ---")
    print(result.best_approach)
    print(f"\n(recommended: level {result.recommended_level})")

    print("\n--- responses ---")
    labels = {
        1: "subtle",
        2: "deniable",
        3: "surgical",
        4: "ruthless",
        5: "nuclear",
    }
    for level in range(1, 6):
        marker = " ← recommended" if level == result.recommended_level else ""
        print(f"\n[{level}] {labels[level]}{marker}")
        print(result.responses[level])

    copy_level = pick or result.recommended_level
    copy_to_clipboard(result.responses[copy_level])
    print(f"\n(copied level {copy_level} to clipboard)")


def _collect_images(paths: list[str]) -> list[Path]:
    images: list[Path] = []
    for p in paths:
        path = Path(p).expanduser()
        if path.is_dir():
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.heic"):
                images.extend(sorted(path.glob(ext)))
        else:
            images.append(path)
    return images


def cmd_argue(args: argparse.Namespace) -> int:
    try:
        if args.text:
            result = argue_from_text(args.text, model=args.model)
        else:
            images = _collect_images(args.images)
            if not images:
                print(
                    "Error: Provide screenshot path(s), or use --text for a transcript.",
                    file=sys.stderr,
                )
                return 1
            result = argue_from_screenshots(
                images,
                vision_model=args.vision_model,
                model=args.model,
            )

        if args.json:
            print(result_to_json(result))
        else:
            _print_result(result, pick=args.pick)

        return 0

    except EnvironmentError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except anthropic.AuthenticationError:
        print(
            "Error: Invalid Anthropic API key. Set ANTHROPIC_API_KEY in .env",
            file=sys.stderr,
        )
        return 1
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="argue",
        description=(
            "Drop in iMessage screenshots, get a logical breakdown "
            "and 5 replies (1=least aggressive, 5=most)."
        ),
    )
    parser.add_argument(
        "images",
        nargs="*",
        help="Screenshot file(s) or folder containing screenshots",
    )
    parser.add_argument(
        "--text",
        help="Skip vision — pass a conversation transcript directly",
    )
    parser.add_argument(
        "--pick",
        type=int,
        choices=[1, 2, 3, 4, 5],
        help="Copy a specific response level to clipboard (default: recommended)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--model", help="Text model override (default: gpt-4.1-mini)")
    parser.add_argument(
        "--vision-model",
        help="Vision model for reading screenshots (default: gpt-4.1-mini)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return cmd_argue(args)


if __name__ == "__main__":
    raise SystemExit(main())
