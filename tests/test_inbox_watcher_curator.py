"""inbox_watcher の curator_request 用 backstage プロンプト整形 unit test。

サザン二重構造 (SPEC.md 後日更新予定) の裏側経路:
  watcher が `to="souther" and message_type="curator_request"` のメッセージを送る時、
  prompt 先頭に `[BACKSTAGE:curator]` sentinel を付加して送信する。inject_souther_mode.py
  はこれを検出して Omage Gate を skip する。

ここでは format ロジックの純関数だけを検証 (asyncio / tmux / DB は触らない)。
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCHER_PATH = REPO_ROOT / "scripts" / "inbox_watcher.py"


@pytest.fixture(scope="module")
def watcher_module():
    spec = importlib.util.spec_from_file_location("inbox_watcher", WATCHER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sample_msg() -> dict:
    return {
        "id": "abcdef12-3456",
        "from_agent": "yuko",
        "to_agent": "souther",
        "message_type": "curator_request",
        "task_id": "case-xyz",
        "content": (
            "memory_proposal 統合依頼。operation=integrate_proposal, "
            "source: data/memory/writer/_proposals/case-xyz.md"
        ),
    }


def test_format_backstage_curator_prompt_has_sentinel(watcher_module):
    out = watcher_module.format_backstage_curator_prompt(_sample_msg())
    # 先頭が sentinel
    assert out.startswith(watcher_module.BACKSTAGE_CURATOR_TAG), (
        f"prompt の先頭が sentinel ({watcher_module.BACKSTAGE_CURATOR_TAG}) ではない: {out[:80]!r}"
    )
    assert watcher_module.BACKSTAGE_CURATOR_TAG == "[BACKSTAGE:curator]"


def test_format_backstage_curator_prompt_includes_content(watcher_module):
    msg = _sample_msg()
    out = watcher_module.format_backstage_curator_prompt(msg)
    assert msg["content"] in out
    assert msg["from_agent"] in out
    assert msg["message_type"] in out
    assert msg["task_id"] in out
    # 末尾の指示文が裏側向け
    assert "memory-curator" in out
    assert "curator_response" in out


def test_format_prompt_does_not_have_sentinel(watcher_module):
    """通常 format_prompt の出力に sentinel が紛れ込まないこと (回帰防止)。"""
    msg = _sample_msg()
    msg["message_type"] = "approval_request"
    out = watcher_module.format_prompt(msg)
    assert watcher_module.BACKSTAGE_CURATOR_TAG not in out, (
        "通常 format_prompt に sentinel が混入している"
    )
    assert "[BACKSTAGE" not in out


# ---------------------------------------------------------------------------
# curator scheduler (cross_review / archive_judge の cron-based トリガー)
# ---------------------------------------------------------------------------


def test_select_overdue_target_returns_oldest(watcher_module):
    """複数 overdue があれば最古を返す。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    state = {
        "client_profile": (now - timedelta(days=40)).isoformat(),  # overdue 古い方
        "quality_bar": (now - timedelta(days=35)).isoformat(),  # overdue 新しめ
        "workflow_rule": (now - timedelta(days=10)).isoformat(),  # まだ
        "recurring_pattern": (now - timedelta(days=29)).isoformat(),  # 境界手前
    }
    selected = watcher_module.select_overdue_target(
        state,
        ["client_profile", "quality_bar", "workflow_rule", "recurring_pattern"],
        interval_days=30,
        now=now,
    )
    assert selected == "client_profile"


def test_select_overdue_target_treats_missing_as_oldest(watcher_module):
    """state に entry が無い候補は最優先 (一度も走っていない扱い)。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    state = {
        "client_profile": (now - timedelta(days=40)).isoformat(),
    }
    selected = watcher_module.select_overdue_target(
        state, ["client_profile", "quality_bar"], interval_days=30, now=now
    )
    # quality_bar (未走) が client_profile (40日経過) より優先
    assert selected == "quality_bar"


def test_select_overdue_target_returns_none_when_all_recent(watcher_module):
    """全候補が interval 内なら None。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    state = {
        "client_profile": (now - timedelta(days=10)).isoformat(),
        "quality_bar": (now - timedelta(days=5)).isoformat(),
    }
    selected = watcher_module.select_overdue_target(
        state, ["client_profile", "quality_bar"], interval_days=30, now=now
    )
    assert selected is None


def test_select_overdue_target_handles_invalid_iso(watcher_module):
    """不正な ISO 文字列は「未走」扱い → 即発火対象。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    state = {"client_profile": "not-an-iso-string"}
    selected = watcher_module.select_overdue_target(
        state, ["client_profile"], interval_days=30, now=now
    )
    assert selected == "client_profile"


def test_build_curator_trigger_content_format(watcher_module):
    """yuko に届く curator_trigger 本文の構造検証。"""
    content = watcher_module.build_curator_trigger_content(
        "cross_review",
        "cross-review-client_profile-2026-05-15",
        {"target_category": "client_profile"},
    )
    assert content.startswith("[curator_trigger]")
    assert "operation=cross_review" in content
    assert "case_id=cross-review-client_profile-2026-05-15" in content
    assert "target_category=client_profile" in content
    assert "consult_souther" in content  # yuko への指示文がある


class _FakeStore:
    """maybe_fire_scheduled_curator_triggers 用のシンプル fake store。"""

    def __init__(self):
        self.messages: list[dict] = []

    async def add_message(
        self,
        from_agent,
        to_agent,
        content,
        message_type,
        task_id=None,
    ):
        self.messages.append(
            {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "content": content,
                "message_type": message_type,
                "task_id": task_id,
            }
        )
        return f"fake-{len(self.messages)}"


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def isolated_schedule(watcher_module, tmp_path, monkeypatch):
    """schedule.json を tmp_path に逃がして本物 data/ を汚さない。"""
    path = tmp_path / "_curator_schedule.json"
    monkeypatch.setattr(watcher_module, "CURATOR_SCHEDULE_PATH", path)
    return path


def test_maybe_fire_scheduler_first_run_fires_both_ops(
    watcher_module, isolated_schedule
):
    """schedule.json が無い初回起動では cross_review と archive_judge を 1 件ずつ発火。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    store = _FakeStore()
    fired = _run(watcher_module.maybe_fire_scheduled_curator_triggers(store, now=now))
    # 2 op (cross_review + archive_judge) で 1 件ずつ
    assert len(fired) == 2
    ops = {f["operation"] for f in fired}
    assert ops == {"cross_review", "archive_judge"}
    # 同じ件数の curator_trigger メッセージが yuko 宛に積まれている
    assert len(store.messages) == 2
    for m in store.messages:
        assert m["to_agent"] == "yuko"
        assert m["from_agent"] == "system"
        assert m["message_type"] == "curator_trigger"
        assert m["task_id"] is not None
        assert m["task_id"] in m["content"]
    # schedule.json が永続化された
    assert isolated_schedule.exists()
    saved = json.loads(isolated_schedule.read_text(encoding="utf-8"))
    assert "cross_review" in saved
    assert "archive_judge" in saved


def test_maybe_fire_scheduler_skips_when_all_recent(
    watcher_module, isolated_schedule
):
    """全 target が interval 内なら何も発火しない。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    # 全 target に「直近 1 日」の last_run を入れる
    recent = (now - timedelta(days=1)).isoformat()
    state = {
        "cross_review": {cat: recent for cat in watcher_module.CROSS_REVIEW_CATEGORIES},
        "archive_judge": {role: recent for role in watcher_module.ARCHIVE_JUDGE_ROLES},
    }
    isolated_schedule.write_text(json.dumps(state), encoding="utf-8")

    store = _FakeStore()
    fired = _run(watcher_module.maybe_fire_scheduled_curator_triggers(store, now=now))
    assert fired == []
    assert store.messages == []


def test_maybe_fire_scheduler_picks_oldest_only(watcher_module, isolated_schedule):
    """同じ op で複数 overdue があっても 1 cycle で発火するのは最古の 1 件。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    state = {
        "cross_review": {
            "client_profile": (now - timedelta(days=40)).isoformat(),  # 最古
            "quality_bar": (now - timedelta(days=35)).isoformat(),
            "workflow_rule": (now - timedelta(days=10)).isoformat(),  # not overdue
            "recurring_pattern": (now - timedelta(days=5)).isoformat(),  # not overdue
        },
        "archive_judge": {
            role: (now - timedelta(days=1)).isoformat()
            for role in watcher_module.ARCHIVE_JUDGE_ROLES
        },
    }
    isolated_schedule.write_text(json.dumps(state), encoding="utf-8")

    store = _FakeStore()
    fired = _run(watcher_module.maybe_fire_scheduled_curator_triggers(store, now=now))
    # cross_review 1 件のみ (最古の client_profile)
    assert len(fired) == 1
    assert fired[0]["operation"] == "cross_review"
    assert fired[0]["target"] == "client_profile"


def test_maybe_fire_scheduler_archive_judge_includes_cutoff(
    watcher_module, isolated_schedule
):
    """archive_judge トリガー本文に cutoff_iso が含まれていること。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    # cross_review 側は全て recent にして archive_judge だけ発火させる
    recent = (now - timedelta(days=1)).isoformat()
    state = {
        "cross_review": {
            cat: recent for cat in watcher_module.CROSS_REVIEW_CATEGORIES
        },
    }
    isolated_schedule.write_text(json.dumps(state), encoding="utf-8")
    store = _FakeStore()
    fired = _run(watcher_module.maybe_fire_scheduled_curator_triggers(store, now=now))

    assert len(fired) == 1
    assert fired[0]["operation"] == "archive_judge"
    msg = store.messages[0]
    assert "target_role=" in msg["content"]
    assert "cutoff_iso=" in msg["content"]


def test_maybe_fire_scheduler_updates_state_to_now(
    watcher_module, isolated_schedule
):
    """発火した target の last_run が now で更新される (= 次の interval まで再発火しない)。"""
    now = datetime(2026, 5, 15, tzinfo=timezone.utc)
    store = _FakeStore()
    _run(watcher_module.maybe_fire_scheduled_curator_triggers(store, now=now))

    saved = json.loads(isolated_schedule.read_text(encoding="utf-8"))
    # 発火した target は last_run が now にセットされる
    fired_cat = saved["cross_review"]
    fired_role = saved["archive_judge"]
    # 一度の cycle で 1 target ずつ発火 = state に 1 entry ずつ書き込まれる
    assert len(fired_cat) == 1
    assert len(fired_role) == 1
    assert list(fired_cat.values())[0] == now.isoformat()
    assert list(fired_role.values())[0] == now.isoformat()

    # 続けて呼ぶと既発火 target は対象外 → 残る overdue target が選ばれる
    store2 = _FakeStore()
    fired2 = _run(watcher_module.maybe_fire_scheduled_curator_triggers(store2, now=now))
    # 2 cycle 目: 残り 3 つの未走 target から 1 件ずつ発火 (cross_review + archive_judge)
    assert len(fired2) == 2
    for f in fired2:
        # 1 cycle 目に発火した target と異なること
        assert f["target"] not in (
            list(fired_cat.keys())[0],
            list(fired_role.keys())[0],
        )
