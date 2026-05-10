"""社長の物理的権限剥奪の検証 (PLAN.md §10.1 サウザー化防止)。

マルチプロセス構成では、社長 (workspaces/souther) の Claude Code プロセスが
permissions.deny で実務ツールを完全に遮断されていることをファイルレベルで保証する。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOUTHER_SETTINGS = REPO_ROOT / "workspaces" / "souther" / ".claude" / "settings.json"
YUKO_SETTINGS = REPO_ROOT / "workspaces" / "yuko" / ".claude" / "settings.json"

SOUTHER_FORBIDDEN_TOOLS = [
    "Bash", "Edit", "Write", "MultiEdit", "NotebookEdit",
    "WebSearch", "WebFetch", "TodoWrite",
    "mcp__itjujiryou__dispatch_task",
    "mcp__itjujiryou__deliver",
    "mcp__itjujiryou__evaluate_deliverable",
    "mcp__itjujiryou__propose_plan",
    "mcp__itjujiryou__consult_souther",
]

SOUTHER_REQUIRED_TOOLS = [
    "mcp__itjujiryou__send_message",
    "mcp__itjujiryou__read_status",
    "Read",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_souther_settings_exists():
    assert SOUTHER_SETTINGS.exists(), f"{SOUTHER_SETTINGS} が存在しない"


def test_souther_denies_all_implementation_tools():
    settings = _load(SOUTHER_SETTINGS)
    deny = settings.get("permissions", {}).get("deny", [])
    for tool in SOUTHER_FORBIDDEN_TOOLS:
        assert tool in deny, (
            f"社長 settings.json に {tool} が deny されていない。サウザー化リスク。"
        )


def test_souther_allows_only_required_tools():
    settings = _load(SOUTHER_SETTINGS)
    allow = settings.get("permissions", {}).get("allow", [])
    for tool in SOUTHER_REQUIRED_TOOLS:
        assert tool in allow, f"社長 settings.json に {tool} が allow されていない"


def test_souther_has_userpromptsubmit_hook():
    """召喚モード block 注入 hook が UserPromptSubmit に登録されていること。"""
    settings = _load(SOUTHER_SETTINGS)
    hooks = settings.get("hooks", {}).get("UserPromptSubmit", [])
    assert hooks, "UserPromptSubmit hook が未登録"
    found = any(
        "inject_souther_mode.py" in (h.get("command") or "")
        for entry in hooks
        for h in entry.get("hooks", [])
    )
    assert found, "inject_souther_mode.py が UserPromptSubmit hook に未登録"


def test_souther_has_recipient_check_hook():
    """social hook: send_message PreToolUse で to=client を deny する hook。"""
    settings = _load(SOUTHER_SETTINGS)
    pre = settings.get("hooks", {}).get("PreToolUse", [])
    found = any(
        "check_souther_recipient.py" in (h.get("command") or "")
        for entry in pre
        if entry.get("matcher") == "mcp__itjujiryou__send_message"
        for h in entry.get("hooks", [])
    )
    assert found, "check_souther_recipient.py が PreToolUse hook に未登録"


def test_yuko_has_persona_leak_hook():
    """ユウコ: deliver と send_message のクライアント宛ペルソナ漏れチェック hook。"""
    settings = _load(YUKO_SETTINGS)
    pre = settings.get("hooks", {}).get("PreToolUse", [])
    matchers_with_check: set[str] = set()
    for entry in pre:
        for h in entry.get("hooks", []):
            if "check_persona_leak.py" in (h.get("command") or ""):
                matchers_with_check.add(entry.get("matcher", ""))
    assert "mcp__itjujiryou__deliver" in matchers_with_check, "deliver の persona-leak hook 不在"
    assert "mcp__itjujiryou__send_message" in matchers_with_check, "send_message の persona-leak hook 不在"


def test_yuko_can_dispatch_and_deliver():
    settings = _load(YUKO_SETTINGS)
    allow = settings.get("permissions", {}).get("allow", [])
    for tool in (
        "mcp__itjujiryou__dispatch_task",
        "mcp__itjujiryou__deliver",
        "mcp__itjujiryou__consult_souther",
        "mcp__itjujiryou__propose_plan",
        "mcp__itjujiryou__evaluate_deliverable",
    ):
        assert tool in allow, f"ユウコ settings.json に {tool} が allow されていない"


def test_souther_claude_md_contains_quotes():
    """社長 CLAUDE.md (本体 + @import モジュール) に名台詞集が含まれていること。
    モジュール化後は本体に直接書かれていないので、_modules/quotes.md も合わせて確認する。"""
    souther_dir = REPO_ROOT / "workspaces" / "souther"
    bodies = [
        (souther_dir / "CLAUDE.md").read_text(encoding="utf-8"),
        (souther_dir / "_modules" / "quotes.md").read_text(encoding="utf-8"),
    ]
    combined = "\n".join(bodies)
    keys = ["天空に極星はふたつはいらぬ", "敵はすべて下郎", "もう一度ぬくもりを"]
    for k in keys:
        assert k in combined, f"名台詞 '{k}' が CLAUDE.md / _modules/quotes.md に含まれていない"
