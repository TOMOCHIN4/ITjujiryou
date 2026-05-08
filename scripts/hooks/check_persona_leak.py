#!/usr/bin/env python3
"""ユウコ pane 用 PreToolUse hook。

`mcp__itjujiryou__deliver` (必ずクライアント宛) と
`mcp__itjujiryou__send_message` (to=client は MCP server 側で deny されるが念のため二重防壁)
の入力に事務所内ペルソナ用語が混入していないかチェックし、
混入があれば exit 2 で deny する。

stdin に PreToolUse の event JSON が来る:
  {"hook_event_name": "PreToolUse", "tool_name": "...", "tool_input": {...}, ...}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.persona import find_forbidden_terms as find_forbidden  # noqa: E402


def main() -> int:
    raw = sys.stdin.read()
    try:
        ev = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # event JSON が読めなければ通す（hook 側の事故で本体を止めない）
        return 0

    tool_name = ev.get("tool_name", "")
    tool_input = ev.get("tool_input", {}) or {}

    # チェック対象を絞る
    if tool_name == "mcp__itjujiryou__deliver":
        target = tool_input.get("delivery_message") or ""
        scope = "deliver/delivery_message (クライアント宛)"
    elif tool_name == "mcp__itjujiryou__send_message":
        # to=client の場合のみ厳格チェック (社内通信ではペルソナ用語は許容)
        if (tool_input.get("to") or "") != "client":
            return 0
        target = tool_input.get("content") or ""
        scope = "send_message/content (to=client)"
    else:
        return 0

    hits = find_forbidden(target)
    if not hits:
        return 0

    sys.stderr.write(
        f"[persona-leak hook] {scope} に事務所内ペルソナ用語が含まれています: {hits}\n"
        "クライアントへ届くテキストから上記の用語を除去してください。\n"
        "（社長の聖帝口調を引用する場合でも、固有名詞は伏せ、平易な現代語に置き換えること）\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
