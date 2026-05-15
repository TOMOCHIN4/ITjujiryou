"""dispatch_task payload 短縮 + structured_ticket 永続化の検証。

ANALYSIS (docs/case_log_analysis/2026-05-14_15.md) §3.3 候補①の対応:
  ticket JSON 全文を dispatch payload に貼っていた実装を廃止し、
  payload は objective + キー一覧のみ。部下は read_status 経由で取得する。
"""
from __future__ import annotations

import json

import pytest

from src.memory.store import Store
import src.mcp_server as mcp_server


@pytest.fixture
async def store(tmp_path, monkeypatch):
    s = Store(db_path=tmp_path / "t.db")
    await s.init()
    # mcp_server.get_store() を fixture の store に向ける
    monkeypatch.setattr(mcp_server, "get_store", lambda: s)
    # outputs ディレクトリ作成側を tmp に差し替え
    monkeypatch.setattr(mcp_server, "OUTPUTS_DIR", tmp_path / "outputs")
    return s


async def test_dispatch_payload_excludes_full_ticket_json(store):
    """payload に ticket JSON 全文 (indent=2 dump) が含まれないこと。"""
    task_id = await store.create_task("t", "d", "r")
    ticket = {
        "objective": "建築 LP のヒーロー画像 1 枚",
        "requirements": ["16:9", "木の温もり", "親子のシルエット"],
        "success_criteria": ["納期本日中"],
        "background_long": "x" * 500,  # 長文 — payload に含まれてはいけない
    }
    args = {
        "from_agent": "yuko",
        "assigned_to": "designer",
        "task_id": task_id,
        "ticket_json": json.dumps(ticket, ensure_ascii=False),
        "preceding_outputs_json": "[]",
    }
    await mcp_server._handle_dispatch_task(args)

    msgs = await store.list_messages(task_id)
    dispatches = [m for m in msgs if m["message_type"] == "dispatch"]
    assert len(dispatches) == 1
    payload = dispatches[0]["content"]

    # 長文 background は payload に出てはいけない (= 旧実装の証拠)
    assert "x" * 500 not in payload
    # ticket dict の indent=2 JSON dump も出てはいけない
    assert '"requirements":' not in payload  # indent=2 dump 特有
    # 一方 objective brief は出てよい
    assert "建築 LP のヒーロー画像" in payload
    # キー一覧と read_status 誘導が出ている
    assert "詳細フィールド:" in payload
    assert "read_status" in payload


async def test_dispatch_persists_structured_ticket(store):
    """dispatch 時に tasks.structured_ticket に ticket 全文が保存される。"""
    task_id = await store.create_task("t", "d", "r")
    ticket = {"objective": "テスト", "requirements": ["a", "b"]}
    args = {
        "from_agent": "yuko",
        "assigned_to": "writer",
        "task_id": task_id,
        "ticket_json": json.dumps(ticket, ensure_ascii=False),
        "preceding_outputs_json": "[]",
    }
    await mcp_server._handle_dispatch_task(args)

    task = await store.get_task(task_id)
    assert task is not None
    assert task["structured_ticket"]
    stored = json.loads(task["structured_ticket"])
    assert stored == ticket


async def test_read_status_returns_structured_ticket(store):
    """read_status の出力に structured_ticket セクションが含まれる。"""
    task_id = await store.create_task("t", "d", "r")
    ticket = {"objective": "テスト案件", "requirements": ["A", "B"]}
    await store.update_task_structured_ticket(
        task_id, json.dumps(ticket, ensure_ascii=False)
    )

    out = await mcp_server._handle_read_status({"task_id": task_id})
    text = out[0].text
    assert "structured_ticket" in text
    assert "テスト案件" in text


async def test_dispatch_payload_preserves_preceding_outputs(store):
    """preceding_outputs はハンドオフに必須なので payload に残ること。"""
    task_id = await store.create_task("t", "d", "r")
    args = {
        "from_agent": "yuko",
        "assigned_to": "engineer",
        "task_id": task_id,
        "ticket_json": json.dumps({"objective": "PNG 化"}),
        "preceding_outputs_json": json.dumps(
            [
                {
                    "from": "designer",
                    "paths": ["outputs/x/eyecatch.svg"],
                    "summary": "viewBox 0 0 1920 1080",
                }
            ]
        ),
    }
    await mcp_server._handle_dispatch_task(args)
    msgs = await store.list_messages(task_id)
    payload = [m for m in msgs if m["message_type"] == "dispatch"][0]["content"]
    assert "preceding_outputs" in payload
    assert "eyecatch.svg" in payload
    assert "viewBox 0 0 1920 1080" in payload
