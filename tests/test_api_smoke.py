"""Phase 2 ダッシュボードのスモークテスト。

実エージェント (claude-agent-sdk) は起動せず、reception を monkeypatch する。
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(monkeypatch, tmp_path_factory):
    # 隔離 DB (tmp_path_factory は Windows でも片付け失敗を ignore してくれる)
    db_path = tmp_path_factory.mktemp("itj") / "test.db"
    monkeypatch.setenv("ITJUJIRYOU_DB_PATH", str(db_path))

    import src.memory.store as store_mod
    store_mod._store_singleton = None  # type: ignore[attr-defined]

    import asyncio
    asyncio.run(store_mod.get_store().init())

    from src.ui.api import app
    yield TestClient(app)
    store_mod._store_singleton = None  # type: ignore[attr-defined]


def test_get_tasks_empty(client):
    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_events_empty(client):
    r = client.get("/api/events?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_staff_5(client):
    r = client.get("/api/staff")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 5
    assert {d["agent"] for d in data} == {"souther", "yuko", "designer", "engineer", "writer"}
    assert all(d["state"] in ("idle", "working") for d in data)


def test_post_order_stub(client, monkeypatch):
    async def fake_handle(text, task_id=None):
        # テスト用に最低限 task を作って文字列を返す
        from src.memory.store import get_store
        await get_store().create_task(title=text[:30], description=text, client_request=text)
        return "テスト納品です。"

    monkeypatch.setattr("src.reception.handle_client_message", fake_handle)
    r = client.post("/api/orders", json={"text": "テスト発注"})
    assert r.status_code == 200
    body = r.json()
    assert body["response"] == "テスト納品です。"
    assert body["task_id"]


def test_ws_snapshot(client):
    with client.websocket_connect("/ws/events") as ws:
        # スナップショット送信は events が空なら何も来ない。
        # 接続自体が確立できれば OK。すぐクローズ。
        # テストとしては「例外なく接続でき、close できる」を確認する。
        pass
