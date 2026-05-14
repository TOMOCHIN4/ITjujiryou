"""記憶システムの物理アクセスガード検証 (SPEC.md §10.1, §10.4, §10.6)。

5 workspaces の settings.json で、他人 personal layer (past_articles 等の topic ディレクトリ)
への Read が **per-topic** で deny されていること、`_proposals/`/`_scratch/` は deny に含まれない
こと (curator/memory-search subagent 経路を確保するため)、Task tool が allow されていること、
ユウコだけは memory への Write 権限を持ち deny がないこと、を静的に検証する。

⚠️ 注 (2026-05-14 更新): 本番運用は `ITJ_PERMISSION_MODE=dontAsk` (`scripts/start_office.sh:46`)
のため `permissions.allow`/`deny` は本番ランタイムでも厳格適用される。本テストは settings.json
の静的検証だが、本番でも効力を持つ。

サザン二重構造 (SPEC.md §10.6) 実装に伴い、Read deny は per-topic に細分化されている。
broad な `Read(.../{role}/**)` 形式 (一括 deny) から、per-topic 形式に移行済。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACES = REPO_ROOT / "workspaces"

ROLES = ("souther", "yuko", "writer", "designer", "engineer")

# 各 role の personal topic (Read deny 対象)。
# `_proposals/` `_scratch/` は curator/memory-search subagent 経路のため deny しない。
PERSONAL_TOPICS = {
    "writer": ("past_articles", "sources", "style_notes"),
    "designer": ("past_works", "style_notes", "techniques"),
    "engineer": ("bugs", "patterns", "preferences"),
    "yuko": ("client_handling", "persona_translation", "routing_decisions"),
    "souther": ("doctrines",),
}


def _load(role: str) -> dict:
    return json.loads(
        (WORKSPACES / role / ".claude" / "settings.json").read_text(encoding="utf-8")
    )


def _read_deny_path(other_role: str, topic: str) -> str:
    # 公式 4 形式: `//path` (絶対パス) を使う。`${CLAUDE_PROJECT_DIR}` は permission rule
    # では展開されない (memory: feedback_permission_rule_glob_format.md 参照)。
    return (
        f"Read(//Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/data/memory/"
        f"{other_role}/{topic}/**)"
    )


def _broad_deny_path(other_role: str) -> str:
    return f"Read(//Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/data/memory/{other_role}/**)"


def test_all_workspaces_allow_task_tool():
    """全 role が Task tool を allow している (subagent 経由の検索のため)。"""
    for role in ROLES:
        allow = _load(role).get("permissions", {}).get("allow", [])
        assert "Task" in allow, f"{role} settings.json に Task が allow されていない"


def _assert_per_topic_deny(role: str, others: tuple[str, ...]) -> None:
    """role が `others` (他人) の personal topic をすべて per-topic で deny していることを検証。"""
    deny = _load(role).get("permissions", {}).get("deny", [])
    for other in others:
        # broad な一括 deny は禁止 (curator が _proposals/_scratch/ を Read できなくなるため)
        assert _broad_deny_path(other) not in deny, (
            f"{role} settings.json で {other} に対する broad deny "
            f"({_broad_deny_path(other)}) が残っている。per-topic に分割せよ"
        )
        # 各 personal topic ごとに deny エントリがあること
        for topic in PERSONAL_TOPICS[other]:
            expected = _read_deny_path(other, topic)
            assert expected in deny, (
                f"{role} settings.json で {other}/{topic}/ Read が deny されていない: "
                f"期待 = {expected}"
            )


def test_writer_denies_other_personal_topics():
    """writer は他 4 人 (designer/engineer/yuko/souther) の personal topic を per-topic で deny。"""
    _assert_per_topic_deny("writer", ("designer", "engineer", "yuko", "souther"))


def test_designer_denies_other_personal_topics():
    _assert_per_topic_deny("designer", ("writer", "engineer", "yuko", "souther"))


def test_engineer_denies_other_personal_topics():
    _assert_per_topic_deny("engineer", ("writer", "designer", "yuko", "souther"))


def test_souther_denies_other_personal_topics():
    """サザンは自分 (doctrines) + 会社 (company/) + 全 role の _proposals/_scratch/ のみ可。
    他 4 人の personal topic (past_articles, client_handling 等) は per-topic で deny。"""
    _assert_per_topic_deny("souther", ("writer", "designer", "engineer", "yuko"))


def test_souther_does_not_deny_proposals_or_scratch():
    """サザンが各 role の `_proposals/` `_scratch/` を Read できる
    (memory-curator subagent が integrate_proposal 等で必要)。"""
    deny = _load("souther").get("permissions", {}).get("deny", [])
    for other in ("writer", "designer", "engineer", "yuko"):
        for sub in ("_proposals", "_scratch"):
            unwanted = (
                f"Read(//Users/tomohiro/Desktop/ClaudeCode/ITjujiryou/data/memory/"
                f"{other}/{sub}/**)"
            )
            assert unwanted not in deny, (
                f"サザン settings.json で {other}/{sub}/ への Read deny が残っている: {unwanted}"
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
