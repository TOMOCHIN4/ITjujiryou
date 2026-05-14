"""記憶整理トリガ (post_deliver_trigger event) の検証。

deliver MCP ツールが events に post_deliver_trigger を insert し、
inbox_watcher が fetch_unprocessed_events / mark_event_processed で拾えること、
format_scratch_consolidation_prompt が正しいプロンプトを返すこと、を確認する。
"""
from __future__ import annotations

import pytest

from src.memory.store import Store
from scripts.inbox_watcher import format_scratch_consolidation_prompt


@pytest.fixture
async def store(tmp_path):
    s = Store(db_path=tmp_path / "t.db")
    await s.init()
    return s


async def test_log_event_post_deliver_trigger_persists(store):
    """log_event で post_deliver_trigger を入れたら fetch_unprocessed_events で拾える。"""
    tid = await store.create_task("t", "d", "r")
    ev_id = await store.log_event(
        "system",
        "post_deliver_trigger",
        tid,
        {"phase": "scratch_to_proposal", "roles": ["writer", "yuko"]},
    )
    assert ev_id > 0

    events = await store.fetch_unprocessed_events("post_deliver_trigger")
    assert len(events) == 1
    e = events[0]
    assert e["task_id"] == tid
    assert e["event_type"] == "post_deliver_trigger"
    assert e["details"]["phase"] == "scratch_to_proposal"
    assert "writer" in e["details"]["roles"]


async def test_mark_event_processed_excludes_from_fetch(store):
    """mark_event_processed したら次回の fetch には現れない。"""
    tid = await store.create_task("t", "d", "r")
    ev_id = await store.log_event(
        "system", "post_deliver_trigger", tid, {"roles": ["writer"]}
    )

    events = await store.fetch_unprocessed_events("post_deliver_trigger")
    assert len(events) == 1

    await store.mark_event_processed(ev_id)

    events = await store.fetch_unprocessed_events("post_deliver_trigger")
    assert len(events) == 0


async def test_fetch_unprocessed_events_filters_by_event_type(store):
    """fetch_unprocessed_events は指定 event_type だけを返す。"""
    tid = await store.create_task("t", "d", "r")
    await store.log_event("system", "post_deliver_trigger", tid, {"roles": ["writer"]})
    await store.log_event("system", "other_event", tid, {})
    await store.log_event("system", "status_change", tid, {"status": "delivered"})

    events = await store.fetch_unprocessed_events("post_deliver_trigger")
    assert len(events) == 1
    assert events[0]["event_type"] == "post_deliver_trigger"


def test_format_scratch_consolidation_prompt_contains_role_and_task():
    """各 role pane に送るプロンプトに role と task_id が含まれる。"""
    prompt = format_scratch_consolidation_prompt("abcd1234-uuid", "writer")
    assert "abcd1234" in prompt
    assert "data/memory/writer/_scratch/abcd1234-uuid/" in prompt
    assert "memory-search subagent" in prompt
    assert "_proposals/abcd1234-uuid.md" in prompt
    assert "memory_proposal" in prompt


def test_format_prompt_role_specific_paths():
    """role ごとに scratch / proposal パスが正しく生成される。"""
    for role in ("writer", "designer", "engineer", "yuko"):
        p = format_scratch_consolidation_prompt("t1", role)
        assert f"data/memory/{role}/_scratch/" in p
        assert f"data/memory/{role}/_proposals/" in p
