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


async def test_last_event_id_empty_returns_zero(store):
    assert await store.last_event_id() == 0


async def test_last_event_id_returns_max_id(store):
    tid = await store.create_task("t", "d", "r")
    # update_task_status は内部で log_event(status_change) を呼ぶ
    await store.update_task_status(tid, "approved")
    eid1 = await store.last_event_id()
    assert eid1 > 0
    await store.update_task_status(tid, "delivered")
    eid2 = await store.last_event_id()
    assert eid2 > eid1


async def test_list_events_since_id_returns_only_newer(store):
    tid = await store.create_task("t", "d", "r")
    await store.update_task_status(tid, "approved")
    cutoff = await store.last_event_id()
    await store.update_task_status(tid, "delivered")
    new_events = await store.list_events(since_id=cutoff)
    assert all(ev["id"] > cutoff for ev in new_events)
    assert len(new_events) >= 1


async def test_get_subtask_assignee_returns_assignee(store):
    tid = await store.create_task("t", "d", "r")
    sid = await store.create_subtask(tid, "writer", "exec")
    assert await store.get_subtask_assignee(sid) == "writer"


async def test_get_subtask_assignee_returns_none_for_unknown(store):
    assert await store.get_subtask_assignee("nonexistent") is None


async def test_list_tasks_filter(store):
    a = await store.create_task("a", "d", "r")
    b = await store.create_task("b", "d", "r")
    await store.update_task_status(b, "approved")
    received = await store.list_tasks(status="received")
    approved = await store.list_tasks(status="approved")
    assert any(t["id"] == a for t in received)
    assert any(t["id"] == b for t in approved)


async def test_list_tasks_q_text_search(store):
    await store.create_task("AIエージェント紹介記事", "AI を扱う記事", "r")
    await store.create_task("ロゴ案", "シンプルなロゴ案を作る", "r")

    titles = [t["title"] for t in await store.list_tasks(q="AI")]
    assert "AIエージェント紹介記事" in titles and "ロゴ案" not in titles

    # 本文 (description) でもヒットすること
    titles = [t["title"] for t in await store.list_tasks(q="シンプル")]
    assert "ロゴ案" in titles


async def test_list_tasks_assigned_to_and_status_and(store):
    import aiosqlite

    a = await store.create_task("alpha", "d", "r")
    b = await store.create_task("beta", "d", "r")
    async with aiosqlite.connect(store.db_path) as db:
        await db.execute("UPDATE tasks SET assigned_to=? WHERE id=?", ("writer", a))
        await db.execute("UPDATE tasks SET assigned_to=? WHERE id=?", ("designer", b))
        await db.commit()
    await store.update_task_status(a, "approved")
    await store.update_task_status(b, "approved")

    rows = await store.list_tasks(status="approved", assigned_to="writer")
    assert [t["id"] for t in rows] == [a]


async def test_list_tasks_date_range(store):
    import aiosqlite

    a = await store.create_task("old", "d", "r")
    b = await store.create_task("new", "d", "r")
    async with aiosqlite.connect(store.db_path) as db:
        await db.execute(
            "UPDATE tasks SET created_at=? WHERE id=?", ("2025-01-01T00:00:00+00:00", a)
        )
        await db.execute(
            "UPDATE tasks SET created_at=? WHERE id=?", ("2026-06-01T00:00:00+00:00", b)
        )
        await db.commit()

    only_new = await store.list_tasks(since="2026-01-01T00:00:00+00:00")
    assert [t["id"] for t in only_new] == [b]

    only_old = await store.list_tasks(until="2025-12-31T23:59:59+00:00")
    assert [t["id"] for t in only_old] == [a]
