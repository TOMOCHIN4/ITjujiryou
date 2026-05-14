"""記憶システムの物理アクセスガード検証 (SPEC.md §10.1, §10.4)。

5 workspaces の settings.json で、他人の data/memory/{role}/** への Read が
deny されていること、Task tool が allow されていること、yuko だけは memory への
Write 権限を持ち deny がないこと、を静的に検証する。

⚠️ 注 (2026-05-14): これは settings.json の **静的検証** であり、本番ランタイムでの
効力を保証するものではない。本番 (`scripts/start_office.sh` が `--dangerously-skip-permissions`
で起動) では `permissions.deny` 全体が skip される (公式 permission-modes.md)。
現状の実質的なアクセス制御は CLAUDE.md の規律 + memory-search subagent プロンプトでの
検索範囲限定のみ。物理ブロック復活は `--permission-mode dontAsk` への切替が必要
(PLAN.md / memory: project_permission_dontask_proposal.md)。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACES = REPO_ROOT / "workspaces"

ROLES = ("souther", "yuko", "writer", "designer", "engineer")


def _load(role: str) -> dict:
    return json.loads(
        (WORKSPACES / role / ".claude" / "settings.json").read_text(encoding="utf-8")
    )


def _read_deny_path(other_role: str) -> str:
    # 公式: `//path` は absolute path from filesystem root の正式書式
    # `${CLAUDE_PROJECT_DIR}` は permission rule では展開されないため使えない
    return f"Read(//Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/data/memory/{other_role}/**)"


def test_all_workspaces_allow_task_tool():
    """全 role が Task tool を allow している (subagent 経由の検索のため)。"""
    for role in ROLES:
        allow = _load(role).get("permissions", {}).get("allow", [])
        assert "Task" in allow, f"{role} settings.json に Task が allow されていない"


def test_writer_denies_other_memory_read():
    """writer は他 4 人 (designer/engineer/yuko/souther) の memory Read を deny。"""
    deny = _load("writer").get("permissions", {}).get("deny", [])
    for other in ("designer", "engineer", "yuko", "souther"):
        assert _read_deny_path(other) in deny, (
            f"writer settings.json で data/memory/{other}/** Read が deny されていない"
        )


def test_designer_denies_other_memory_read():
    deny = _load("designer").get("permissions", {}).get("deny", [])
    for other in ("writer", "engineer", "yuko", "souther"):
        assert _read_deny_path(other) in deny, (
            f"designer settings.json で data/memory/{other}/** Read が deny されていない"
        )


def test_engineer_denies_other_memory_read():
    deny = _load("engineer").get("permissions", {}).get("deny", [])
    for other in ("writer", "designer", "yuko", "souther"):
        assert _read_deny_path(other) in deny, (
            f"engineer settings.json で data/memory/{other}/** Read が deny されていない"
        )


def test_souther_denies_other_memory_read():
    """サザンは自分 + 会社 (company/) のみ可。三兄弟 + ユウコ の memory Read を deny。"""
    deny = _load("souther").get("permissions", {}).get("deny", [])
    for other in ("writer", "designer", "engineer", "yuko"):
        assert _read_deny_path(other) in deny, (
            f"souther settings.json で data/memory/{other}/** Read が deny されていない"
        )


def test_yuko_has_no_memory_read_deny():
    """ユウコは全閲覧可なので、data/memory/{*}/** の Read deny は一切ないこと。"""
    deny = _load("yuko").get("permissions", {}).get("deny", [])
    for entry in deny:
        assert "data/memory/" not in entry or "Read(" not in entry, (
            f"ユウコ settings.json に memory Read deny が混入: {entry}"
        )


def test_yuko_can_write_own_memory():
    """ユウコは自身の memory 領域への Write 権限を持つ。"""
    allow = _load("yuko").get("permissions", {}).get("allow", [])
    assert "Write(//Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/data/memory/yuko/**)" in allow, (
        "ユウコ settings.json に data/memory/yuko/** Write 権限がない"
    )


def test_yuko_can_write_company_proposals():
    """ユウコは会社記憶の _proposals (統合済提案の置き場) に書き込める。"""
    allow = _load("yuko").get("permissions", {}).get("allow", [])
    assert (
        "Write(//Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/data/memory/company/_proposals/**)" in allow
    ), "ユウコ settings.json に data/memory/company/_proposals/** Write 権限がない"


def test_three_brothers_can_write_own_memory():
    """三兄弟は各自の memory 領域へ書き込める (既存設定の retain)。"""
    for role in ("writer", "designer", "engineer"):
        allow = _load(role).get("permissions", {}).get("allow", [])
        path = f"Write(//Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/data/memory/{role}/**)"
        assert path in allow, f"{role} settings.json に {path} が allow されていない"
