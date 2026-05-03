"""dispatch_task ツールが構造化チケット必須であること、subtask が DB に残ること。

エージェント起動部分はモックする。
"""
import json
from unittest.mock import patch, AsyncMock

import pytest

from src.tools import registry as reg
from src.memory.store import Store


@pytest.fixture
async def store(tmp_path):
    s = Store(db_path=tmp_path / "test.db")
    await s.init()
    # シングルトンを差し替え
    import src.memory.store as store_mod
    store_mod._store_singleton = s
    yield s
    store_mod._store_singleton = None


async def test_dispatch_creates_subtask_and_invokes_subordinate(store):
    task_id = await store.create_task("test", "test desc", "test req")

    ticket = {
        "objective": "テスト記事を書く",
        "background": "background",
        "requirements": {"deliverable": "md", "format": "markdown", "scope": "300字"},
        "success_criteria": ["完了"],
        "constraints": [],
        "references": [],
        "deadline": "2026-05-10",
    }

    with patch("src.tools.registry.run_agent", new=AsyncMock(return_value="完了報告: テスト記事を執筆しました。")):
        result = await reg.dispatch_task_tool.handler({
            "assigned_to": "writer",
            "task_id": task_id,
            "ticket_json": json.dumps(ticket, ensure_ascii=False),
        })

    text = result["content"][0]["text"]
    assert "完了報告" in text
    subs = await store.list_subtasks(task_id)
    assert len(subs) == 1
    assert subs[0]["assigned_to"] == "writer"
    assert subs[0]["status"] == "done"


async def test_dispatch_rejects_invalid_assignee(store):
    task_id = await store.create_task("t", "d", "r")
    result = await reg.dispatch_task_tool.handler({
        "assigned_to": "souther",  # 社長は dispatch 対象ではない
        "task_id": task_id,
        "ticket_json": "{}",
    })
    assert "ERROR" in result["content"][0]["text"]


async def test_dispatch_rejects_invalid_json(store):
    task_id = await store.create_task("t", "d", "r")
    result = await reg.dispatch_task_tool.handler({
        "assigned_to": "writer",
        "task_id": task_id,
        "ticket_json": "not json",
    })
    assert "ERROR" in result["content"][0]["text"]
