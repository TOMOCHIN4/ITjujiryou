"""SQLite 永続化の薄いラッパ。"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiosqlite

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "office.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class Store:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(os.environ.get("ITJUJIRYOU_DB_PATH", db_path or DEFAULT_DB_PATH))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(schema)
            await db.commit()

    # --- tasks ---
    async def create_task(
        self,
        title: str,
        description: str,
        client_request: str,
        deadline: Optional[str] = None,
    ) -> str:
        task_id = _new_id()
        now = _now()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO tasks (id, title, description, status, client_request, "
                "created_at, updated_at, deadline) VALUES (?,?,?,?,?,?,?,?)",
                (task_id, title, description, "received", client_request, now, now, deadline),
            )
            await db.commit()
        return task_id

    async def update_task_status(
        self, task_id: str, status: str, notes: Optional[str] = None
    ) -> None:
        now = _now()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE id=?",
                (status, now, task_id),
            )
            if status == "delivered":
                await db.execute(
                    "UPDATE tasks SET completed_at=? WHERE id=?", (now, task_id)
                )
            await db.commit()
        await self.log_event("system", "status_change", task_id, {"status": status, "notes": notes})

    async def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_tasks(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cur = await db.execute(
                    "SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC", (status,)
                )
            else:
                cur = await db.execute("SELECT * FROM tasks ORDER BY created_at DESC")
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # --- subtasks ---
    async def create_subtask(
        self, parent_task_id: str, assigned_to: str, description: str
    ) -> str:
        sub_id = _new_id()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO subtasks (id, parent_task_id, assigned_to, description, status, "
                "created_at) VALUES (?,?,?,?,?,?)",
                (sub_id, parent_task_id, assigned_to, description, "in_progress", _now()),
            )
            await db.commit()
        return sub_id

    async def complete_subtask(self, sub_id: str, deliverable_path: Optional[str] = None) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE subtasks SET status='done', completed_at=?, deliverable_path=? WHERE id=?",
                (_now(), deliverable_path, sub_id),
            )
            await db.commit()

    async def list_subtasks(self, parent_task_id: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM subtasks WHERE parent_task_id=? ORDER BY created_at",
                (parent_task_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    # --- messages ---
    async def add_message(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        message_type: str,
        task_id: Optional[str] = None,
    ) -> str:
        msg_id = _new_id()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO messages (id, task_id, from_agent, to_agent, content, "
                "message_type, timestamp) VALUES (?,?,?,?,?,?,?)",
                (msg_id, task_id, from_agent, to_agent, content, message_type, _now()),
            )
            await db.commit()
        return msg_id

    async def list_messages(self, task_id: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM messages WHERE task_id=? ORDER BY timestamp", (task_id,)
            )
            return [dict(r) for r in await cur.fetchall()]

    # --- deliverables ---
    async def add_deliverable(
        self,
        task_id: str,
        file_path: str,
        created_by: str,
        file_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> str:
        d_id = _new_id()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO deliverables (id, task_id, file_path, file_type, created_by, "
                "description, created_at) VALUES (?,?,?,?,?,?,?)",
                (d_id, task_id, file_path, file_type, created_by, description, _now()),
            )
            await db.commit()
        return d_id

    # --- plans (Phase 1.5) ---
    async def add_plan(self, task_id: str, plan_json: str) -> str:
        plan_id = _new_id()
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT COALESCE(MAX(version),0)+1 FROM plans WHERE task_id=?", (task_id,)
            )
            (version,) = await cur.fetchone()
            await db.execute(
                "INSERT INTO plans (id, task_id, version, plan_json, created_at) "
                "VALUES (?,?,?,?,?)",
                (plan_id, task_id, version, plan_json, _now()),
            )
            await db.commit()
        return plan_id

    async def get_latest_plan(self, task_id: str) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM plans WHERE task_id=? ORDER BY version DESC LIMIT 1",
                (task_id,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None

    # --- revisions (Phase 1.5) ---
    async def add_revision(
        self,
        task_id: str,
        subtask_id: str,
        round_: int,
        evaluation: str,
        decision: str,
    ) -> str:
        rev_id = _new_id()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO revisions (id, task_id, subtask_id, round, evaluation, "
                "decision, created_at) VALUES (?,?,?,?,?,?,?)",
                (rev_id, task_id, subtask_id, round_, evaluation, decision, _now()),
            )
            await db.commit()
        return rev_id

    async def count_revisions(self, subtask_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM revisions WHERE subtask_id=? AND decision='revise'",
                (subtask_id,),
            )
            (n,) = await cur.fetchone()
            return n

    async def list_revisions(self, task_id: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM revisions WHERE task_id=? ORDER BY created_at",
                (task_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def count_agent_calls(self, task_id: str) -> int:
        """events テーブルから案件内のエージェント起動回数 (agent_start) を数える。"""
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM events WHERE task_id=? AND event_type='agent_start'",
                (task_id,),
            )
            (n,) = await cur.fetchone()
            return n

    async def count_consult_pair(self, task_id: str, from_agent: str, to_agent: str) -> int:
        """同一 (from→to) ペアの consult メッセージ件数。"""
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE task_id=? AND from_agent=? "
                "AND to_agent=? AND message_type='consult'",
                (task_id, from_agent, to_agent),
            )
            (n,) = await cur.fetchone()
            return n

    # --- events ---
    async def log_event(
        self,
        agent: str,
        event_type: str,
        task_id: Optional[str],
        details: Optional[dict] = None,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO events (timestamp, agent, event_type, task_id, details) "
                "VALUES (?,?,?,?,?)",
                (_now(), agent, event_type, task_id, json.dumps(details or {}, ensure_ascii=False)),
            )
            await db.commit()


_store_singleton: Optional[Store] = None


def get_store() -> Store:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = Store()
    return _store_singleton
