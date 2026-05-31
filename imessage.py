"""Send iMessages via AppleScript."""

from __future__ import annotations

import subprocess


def _escape_applescript(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def send_imessage(phone_number: str, text: str) -> None:
    escaped = _escape_applescript(text)
    script = (
        'tell application "Messages"\n'
        f'    send "{escaped}" to chat id "iMessage;-;{phone_number}"\n'
        'end tell'
    )
    subprocess.run(["osascript", "-e", script], check=True)
