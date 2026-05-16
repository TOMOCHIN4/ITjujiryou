#!/usr/bin/env python3
"""UserPromptSubmit hook: 開発レイヤーの Phase 進行状態を context に注入する。

入力 (stdin): Claude Code hook が渡す JSON (session_id / prompt 等)。本 hook は内容を見ない。
出力 (stdout): {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "..."}}

参照する真実源: .claude/phase_state.json (project root 相対)
読めない / 不正な場合は静かに空出力で終了 (= 開発作業を止めない)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _find_phase_state() -> Path | None:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / ".claude" / "phase_state.json"
        if candidate.is_file():
            return candidate
    return None


def _format_context(state: dict) -> str:
    phase = state.get("phase", "?")
    sub_step = state.get("sub_step_current", "?")
    remaining = state.get("sub_step_remaining", "?")
    goal = state.get("phase_simple_goal", "(未設定)")
    plan_path = state.get("latest_plan_path", "(未設定)")
    return (
        f"[Phase {phase}, Sub-Step {sub_step} / 残 {remaining} step]\n"
        f"シンプルゴール: {goal}\n"
        f"最新プラン: {plan_path}"
    )


def main() -> int:
    try:
        sys.stdin.read()
    except Exception:
        pass

    state_path = _find_phase_state()
    if state_path is None:
        return 0

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"inject_phase: phase_state.json 読込失敗: {exc}", file=sys.stderr)
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _format_context(state),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
