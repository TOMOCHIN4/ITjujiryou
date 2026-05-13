#!/usr/bin/env python3
"""社長 pane 用 PreToolUse hook。

サザン (souther workspace) が `send_message` を呼ぶ際、宛先 (to) が `yuko` 以外
であれば deny する。Omage Gate 設計上、サザンはユウコとしか会話しない
(SPEC.md §4.1, §7.1 参照)。

stdin に PreToolUse の event JSON が来る:
  {"hook_event_name": "PreToolUse", "tool_name": "...", "tool_input": {...}, ...}
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    if ev.get("tool_name", "") != "mcp__itjujiryou__send_message":
        return 0

    tool_input = ev.get("tool_input", {}) or {}
    to = (tool_input.get("to") or "").strip()
    if to != "yuko":
        sys.stderr.write(
            f"[souther-recipient hook] サザンはユウコとしか会話しない (Omage Gate)。"
            f"to='{to}' は deny。to='yuko' + message_type='approval' で応答せよ。\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
