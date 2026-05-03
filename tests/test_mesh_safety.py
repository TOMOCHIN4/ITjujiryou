"""Phase 1.5 メッシュ協業の暴走防止ロジック検証。

- consult_peer の depth 上限
- (from→to) ピンポン上限
- evaluate_deliverable の修正サイクル上限 → 自動 escalate
- propose_plan の保存
- dispatch_task の preceding_outputs / revision_round の受け渡し
"""
from __future__ import annotations

import json
from unittest.mock import patch, AsyncMock

import pytest

from src.tools import registry as reg
from src.memory.store import Store


@pytest.fixture
async def store(tmp_path):
    s = Store(db_path=tmp_path / "mesh.db")
    await s.init()
    import src.memory.store as store_mod
    store_mod._store_singleton = s
    yield s
    store_mod._store_singleton = None


# --- depth 上限 -----------------------------------------------------------
async def test_consult_peer_blocks_at_max_depth(store):
    task_id = await store.create_task("t", "d", "r")

    # depth 2 (peer 経由) で追加 consult を試みる: NG
    chain = [("yuko", 0), ("writer", 1), ("designer", 2)]
    token = reg._call_chain.set(chain)
    try:
        result = await reg.consult_peer_tool.handler({
            "from_agent": "designer",
            "to": "engineer",
            "task_id": task_id,
            "question": "test",
            "context": "",
        })
    finally:
        reg._call_chain.reset(token)
    assert "ERROR" in result["content"][0]["text"]
    assert "深度" in result["content"][0]["text"]


async def test_consult_peer_allowed_at_depth_one(store):
    """depth=1 (yuko→writer) からの consult は許可されること (run_agent はモック)。"""
    task_id = await store.create_task("t", "d", "r")
    chain = [("yuko", 0), ("writer", 1)]
    token = reg._call_chain.set(chain)
    try:
        with patch("src.tools.registry.run_agent", new=AsyncMock(return_value="デザイナー応答")):
            result = await reg.consult_peer_tool.handler({
                "from_agent": "writer",
                "to": "designer",
                "task_id": task_id,
                "question": "挿絵案を",
                "context": "記事冒頭用",
            })
    finally:
        reg._call_chain.reset(token)
    assert "ERROR" not in result["content"][0]["text"]
    assert "デザイナー応答" in result["content"][0]["text"]


# --- ピンポン上限 ---------------------------------------------------------
async def test_consult_peer_pingpong_limit(store):
    task_id = await store.create_task("t", "d", "r")
    chain = [("yuko", 0), ("writer", 1)]
    token = reg._call_chain.set(chain)
    try:
        with patch("src.tools.registry.run_agent", new=AsyncMock(return_value="ok")):
            for _ in range(reg.MAX_CONSULT_PAIR):
                r = await reg.consult_peer_tool.handler({
                    "from_agent": "writer",
                    "to": "designer",
                    "task_id": task_id,
                    "question": "q",
                    "context": "",
                })
                assert "ERROR" not in r["content"][0]["text"]
            # 上限超過
            r = await reg.consult_peer_tool.handler({
                "from_agent": "writer",
                "to": "designer",
                "task_id": task_id,
                "question": "q",
                "context": "",
            })
    finally:
        reg._call_chain.reset(token)
    assert "ERROR" in r["content"][0]["text"]
    assert "上限" in r["content"][0]["text"]


# --- 権限チェック ---------------------------------------------------------
async def test_consult_peer_rejects_non_subordinate_caller(store):
    task_id = await store.create_task("t", "d", "r")
    r = await reg.consult_peer_tool.handler({
        "from_agent": "yuko",
        "to": "designer",
        "task_id": task_id,
        "question": "q",
        "context": "",
    })
    assert "ERROR" in r["content"][0]["text"]


async def test_consult_peer_rejects_self_consult(store):
    task_id = await store.create_task("t", "d", "r")
    chain = [("yuko", 0), ("writer", 1)]
    token = reg._call_chain.set(chain)
    try:
        r = await reg.consult_peer_tool.handler({
            "from_agent": "writer",
            "to": "writer",
            "task_id": task_id,
            "question": "q",
            "context": "",
        })
    finally:
        reg._call_chain.reset(token)
    assert "ERROR" in r["content"][0]["text"]


# --- evaluate_deliverable サイクル ----------------------------------------
async def test_evaluate_revise_within_limit_records(store):
    task_id = await store.create_task("t", "d", "r")
    sub_id = await store.create_subtask(task_id, "writer", "exec")

    r = await reg.evaluate_deliverable_tool.handler({
        "task_id": task_id,
        "subtask_id": sub_id,
        "evaluation": "見出しが弱い",
        "decision": "revise",
        "round": 0,
    })
    assert "ERROR" not in r["content"][0]["text"]
    assert "decision=revise" in r["content"][0]["text"]
    assert await store.count_revisions(sub_id) == 1


async def test_evaluate_revise_over_limit_auto_escalates(store):
    task_id = await store.create_task("t", "d", "r")
    sub_id = await store.create_subtask(task_id, "writer", "exec")

    # MAX_REVISION_ROUNDS 回まで revise OK
    for i in range(reg.MAX_REVISION_ROUNDS):
        r = await reg.evaluate_deliverable_tool.handler({
            "task_id": task_id,
            "subtask_id": sub_id,
            "evaluation": f"修正{i+1}回目",
            "decision": "revise",
            "round": i,
        })
        assert "decision=revise" in r["content"][0]["text"]

    # 上限超過: 自動 escalate
    r = await reg.evaluate_deliverable_tool.handler({
        "task_id": task_id,
        "subtask_id": sub_id,
        "evaluation": "更に修正",
        "decision": "revise",
        "round": reg.MAX_REVISION_ROUNDS,
    })
    text = r["content"][0]["text"]
    assert "decision=escalate_to_president" in text
    assert "自動的に" in text


async def test_evaluate_invalid_decision(store):
    task_id = await store.create_task("t", "d", "r")
    sub_id = await store.create_subtask(task_id, "writer", "exec")
    r = await reg.evaluate_deliverable_tool.handler({
        "task_id": task_id,
        "subtask_id": sub_id,
        "evaluation": "x",
        "decision": "yolo",
        "round": 0,
    })
    assert "ERROR" in r["content"][0]["text"]


# --- propose_plan ---------------------------------------------------------
async def test_propose_plan_saves(store):
    task_id = await store.create_task("t", "d", "r")
    plan = {"steps": [{"step": "design", "assignee": "designer"}], "risks": []}
    r = await reg.propose_plan_tool.handler({
        "task_id": task_id,
        "plan_json": json.dumps(plan, ensure_ascii=False),
    })
    assert "ERROR" not in r["content"][0]["text"]
    saved = await store.get_latest_plan(task_id)
    assert saved is not None
    assert saved["version"] == 1
    assert "design" in saved["plan_json"]


async def test_propose_plan_rejects_invalid_json(store):
    task_id = await store.create_task("t", "d", "r")
    r = await reg.propose_plan_tool.handler({
        "task_id": task_id,
        "plan_json": "not json",
    })
    assert "ERROR" in r["content"][0]["text"]


# --- dispatch_task with preceding_outputs / revision_round ---------------
async def test_dispatch_with_preceding_outputs(store):
    task_id = await store.create_task("t", "d", "r")
    chain = [("yuko", 0)]
    token = reg._call_chain.set(chain)
    try:
        with patch("src.tools.registry.run_agent", new=AsyncMock(return_value="OK")):
            r = await reg.dispatch_task_tool.handler({
                "assigned_to": "engineer",
                "task_id": task_id,
                "ticket_json": json.dumps({"objective": "build LP"}, ensure_ascii=False),
                "preceding_outputs_json": json.dumps([
                    {"from": "designer", "paths": ["a.svg"], "summary": "logo"}
                ], ensure_ascii=False),
                "revision_round": 0,
            }, )
    finally:
        reg._call_chain.reset(token)
    assert "ERROR" not in r["content"][0]["text"]


async def test_dispatch_revision_over_limit_blocked(store):
    task_id = await store.create_task("t", "d", "r")
    sub_id = await store.create_subtask(task_id, "writer", "x")
    chain = [("yuko", 0)]
    token = reg._call_chain.set(chain)
    try:
        with patch("src.tools.registry.run_agent", new=AsyncMock(return_value="OK")):
            r = await reg.dispatch_task_tool.handler({
                "assigned_to": "writer",
                "task_id": task_id,
                "ticket_json": json.dumps({"objective": "fix"}, ensure_ascii=False),
                "preceding_outputs_json": "[]",
                "revision_round": reg.MAX_REVISION_ROUNDS + 1,
                "subtask_id": sub_id,
            })
    finally:
        reg._call_chain.reset(token)
    assert "ERROR" in r["content"][0]["text"]
    assert "上限" in r["content"][0]["text"]
