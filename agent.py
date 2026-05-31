#!/usr/bin/env python3
"""Argue Bot agent — paste a conversation, pick a reply, send it."""

from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv(override=True)

from analyzer import argue_from_text
from imessage import send_imessage

LABELS = {
    1: "subtle",
    2: "deniable",
    3: "surgical",
    4: "ruthless",
    5: "nuclear",
}


def read_conversation() -> str:
    print("\nPaste the conversation (press Enter twice when done):\n")
    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
            lines.append(line)
        else:
            empty_count = 0
            lines.append(line)
    return "\n".join(lines).strip()


def show_analysis(result):
    print(f"\n--- situation ---\n{result.situation}")
    print(f"\n--- breakdown ---\n{result.breakdown}")
    print(f"\n--- best approach ---\n{result.best_approach}")
    print(f"\n(recommended: level {result.recommended_level})")

    print("\n--- responses ---")
    for level in range(1, 6):
        marker = " ← recommended" if level == result.recommended_level else ""
        print(f"\n  [{level}] {LABELS[level]}{marker}")
        print(f"  {result.responses[level]}")
    print()


def main():
    phone = input("Their phone number (e.g. +1234567890): ").strip()
    if not phone:
        print("Need a phone number to send replies.")
        return 1

    conversation = read_conversation()
    if not conversation:
        print("No conversation provided.")
        return 1

    print("\nAnalyzing...\n")
    result = argue_from_text(conversation)
    show_analysis(result)

    while True:
        choice = input("Send a response? (1-5 / n): ").strip().lower()
        if choice == "n":
            print("Nothing sent.")
            return 0
        if choice.isdigit() and 1 <= int(choice) <= 5:
            break
        print("Pick 1-5 or n to cancel.")

    level = int(choice)
    reply = result.responses[level]

    print(f"\nSending [{LABELS[level]}]:\n  {reply}\n")
    confirm = input(f"Send to {phone}? (y/n): ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return 0

    try:
        send_imessage(phone, reply)
        print("Sent!")
    except Exception as e:
        print(f"Failed to send: {e}", file=sys.stderr)
        print(f"\nCopy this instead:\n{reply}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
