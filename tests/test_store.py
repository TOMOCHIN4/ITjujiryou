"""Store の基本 CRUD が動くこと。"""
import pytest

from src.memory.store import Store


@pytest.fixture
async def store(tmp_path):
    s = Store(db_path=tmp_path / "t.db")
    await s.init()
    return s


async def test_create_and_get_task(store):
    tid = await store.create_task("title", "desc", "client req")
    task = await store.get_task(tid)
    assert task is not None
    assert task["title"] == "title"
    assert task["status"] == "received"


async def test_status_transition(store):
    tid = await store.create_task("t", "d", "r")
    await store.update_task_status(tid, "approved")
    assert (await store.get_task(tid))["status"] == "approved"
    await store.update_task_status(tid, "delivered")
    task = await store.get_task(tid)
    assert task["status"] == "delivered"
    assert task["completed_at"] is not None


async def test_messages_and_subtasks(store):
    tid = await store.create_task("t", "d", "r")
    await store.add_message("client", "yuko", "hi", "email", tid)
    msgs = await store.list_messages(tid)
    assert len(msgs) == 1

    sub_id = await store.create_subtask(tid, "writer", "exec")
    await store.complete_subtask(sub_id, "/path/to/out")
    subs = await store.list_subtasks(tid)
    assert subs[0]["status"] == "done"
    assert subs[0]["deliverable_path"] == "/path/to/out"


async def test_create_subtask_with_explicit_id_persists(store):
    """ユウコがラベル付き subtask_id を渡しても行が永続化されること。"""
    tid = await store.create_task("t", "d", "r")
    sid = await store.create_subtask(tid, "writer", "exec", sub_id="writing-001")
    assert sid == "writing-001"
    subs = await store.list_subtasks(tid)
    assert len(subs) == 1 and subs[0]["id"] == "writing-001"


async def test_create_subtask_explicit_id_idempotent(store):
    """同じ explicit id で再呼出ししても重複行が増えず、既存行を返すこと (revision)。"""
    tid = await store.create_task("t", "d", "r")
    sid1 = await store.create_subtask(tid, "writer", "exec", sub_id="writing-001")
    sid2 = await store.create_subtask(tid, "writer", "exec (revised)", sub_id="writing-001")
    assert sid1 == sid2
    subs = await store.list_subtasks(tid)
    assert len(subs) == 1


async def test_list_tasks_filter(store):
    a = await store.create_task("a", "d", "r")
    b = await store.create_task("b", "d", "r")
    await store.update_task_status(b, "approved")
    received = await store.list_tasks(status="received")
    approved = await store.list_tasks(status="approved")
    assert any(t["id"] == a for t in received)
    assert any(t["id"] == b for t in approved)
