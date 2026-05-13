#!/usr/bin/env python3
"""社長 pane 用 PreToolUse hook。

社長 (sauther workspace) が `send_message` を呼ぶ際、宛先 (to) が `client` で
あれば deny する。聖帝はクライアントと直接会話しない (SPEC.md §4.1, §6 参照)。

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
    if to == "client":
        sys.stderr.write(
            "[souther-recipient hook] 聖帝はクライアントと直接会話しない。"
            "ユウコ宛 (to='yuko') に message_type='approval' などで応答せよ。\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
