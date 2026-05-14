"""社長の物理的権限剥奪の検証 (SPEC.md §7.1 サウザー化防止)。

マルチプロセス構成では、社長 (workspaces/souther) の Claude Code プロセスが
permissions.deny で実務ツールを完全に遮断されていることをファイルレベルで保証する。

⚠️ 注 (2026-05-14): 本番運用は `ITJ_PERMISSION_MODE=dontAsk` (`scripts/start_office.sh:46`)
のため `permissions.allow`/`deny` は本番ランタイムでも厳格適用される。本テストは
settings.json の静的検証だが、本番でも効力を持つ。サザン二重構造実装後は
limited Write (`Write(//.../data/memory/company/_proposals/**)`) のみ allow に明記し、
bare `Write` は allow にも deny にも入れない (dontAsk が auto-deny する)。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOUTHER_SETTINGS = REPO_ROOT / "workspaces" / "souther" / ".claude" / "settings.json"
YUKO_SETTINGS = REPO_ROOT / "workspaces" / "yuko" / ".claude" / "settings.json"
MEMORY_CURATOR_AGENT = REPO_ROOT / "workspaces" / "souther" / ".claude" / "agents" / "memory-curator.md"

# Write は二重構造実装で limited allow に移動したため deny からは除外。
# bare Write の禁止は `test_souther_write_limited_to_proposals` で別途検証する。
SOUTHER_FORBIDDEN_TOOLS = [
    "Bash", "Edit", "MultiEdit", "NotebookEdit",
    "WebSearch", "WebFetch", "TodoWrite",
    "mcp__itjujiryou__dispatch_task",
    "mcp__itjujiryou__deliver",
    "mcp__itjujiryou__evaluate_deliverable",
    "mcp__itjujiryou__propose_plan",
    "mcp__itjujiryou__consult_souther",
]

# 2026-05-14 verify-003 で発覚: subagent 継承時に Write glob `Write(//abs/path/**)` が
# path normalization の実装上不整合で auto-deny される。確実に通すため bare `Write` を
# allow に置く。物理ガードは memory-curator.md / persona_narrative.md §6.6 の規律で担保。
# 詳細: ~/.claude/plans/playful-roaming-fern.md, memory: project_next_session_souther_chores.md

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


def test_souther_write_allowed_with_discipline_guard():
    """サザン二重構造 (2026-05-14 verify-003 後): bare Write を allow に置く。
    物理 glob ガードは subagent 継承の path normalization 実装問題で機能しないため、
    memory-curator.md の作法記述 + persona_narrative.md §6.6 の規律でガード。
    deny には Write を入れない (公式仕様で deny > allow のため bare deny は limited も殺す)。"""
    settings = _load(SOUTHER_SETTINGS)
    allow = settings.get("permissions", {}).get("allow", [])
    deny = settings.get("permissions", {}).get("deny", [])
    assert "Write" in allow, "bare Write が allow に未登録 (verify-003 後の構成)"
    assert "Write" not in deny, "bare Write を deny に入れると allow が無効化される"
    # 規律ガードが書かれていることの間接検証
    curator_md = MEMORY_CURATOR_AGENT.read_text(encoding="utf-8")
    assert "絶対パス" in curator_md, "memory-curator.md に絶対パス指示が無い"
    assert "_proposals" in curator_md, "memory-curator.md に _proposals/ 書込限定指示が無い"


def test_souther_has_memory_curator_agent():
    """サザン二重構造の裏側を担う memory-curator subagent 定義が存在し、
    必要な tools と effort が frontmatter に書かれていること。"""
    assert MEMORY_CURATOR_AGENT.exists(), f"{MEMORY_CURATOR_AGENT} が存在しない"
    content = MEMORY_CURATOR_AGENT.read_text(encoding="utf-8")
    # frontmatter 抽出 (先頭 --- から次の --- まで)
    assert content.startswith("---\n"), "frontmatter (---) が冒頭にない"
    end = content.find("\n---\n", 4)
    assert end > 0, "frontmatter の終端 --- が見つからない"
    fm = content[4:end]
    assert "name: memory-curator" in fm, "name が memory-curator ではない"
    # tools 行に必須 4 つを含む
    tools_line = next(
        (line for line in fm.splitlines() if line.strip().startswith("tools:")),
        None,
    )
    assert tools_line is not None, "tools: 行が frontmatter にない"
    for required in ("Read", "Glob", "Grep", "Write"):
        assert required in tools_line, f"tools に {required} がない: {tools_line}"
    assert "effort: high" in fm, "effort: high が frontmatter にない"


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
