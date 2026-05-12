"""SQLite 永続化の薄いラッパ。

マルチプロセス前提 (Phase 2.3〜) のため WAL モード + busy_timeout で並行アクセス耐性を上げる。
"""
from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiosqlite

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = REPO_ROOT / "data" / "office.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

_BUSY_TIMEOUT_MS = 30000
_CONNECT_TIMEOUT_S = 30.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class Store:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(os.environ.get("ITJUJIRYOU_DB_PATH", db_path or DEFAULT_DB_PATH))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def _connect(self):
        async with aiosqlite.connect(self.db_path, timeout=_CONNECT_TIMEOUT_S) as db:
            await db.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
            yield db

    async def init(self) -> None:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        async with aiosqlite.connect(self.db_path, timeout=_CONNECT_TIMEOUT_S) as db:
            await db.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")
            # 既存テーブルへの新規列 ADD は executescript の前に行う必要がある
            # (schema.sql 内に新規列を参照する部分インデックスがあるため)
            await self._migrate(db)
            await db.executescript(schema)
            await db.commit()

    async def _migrate(self, db) -> None:
        """既存 DB に新規列を ADD COLUMN する (CREATE TABLE IF NOT EXISTS では既存テーブルに列が増えないため)。
        テーブル自体が存在しない場合 (新規 DB) は何もしない — 後続の executescript で作成される。"""

        async def add_if_missing(table: str, column: str, ddl: str) -> None:
            cur = await db.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in await cur.fetchall()]
            if not cols:
                return  # テーブル未作成 (新規 DB)
            if column not in cols:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

        async def drop_if_present(table: str, column: str) -> None:
            cur = await db.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in await cur.fetchall()]
            if column in cols:
                await db.execute(f"ALTER TABLE {table} DROP COLUMN {column}")

        await add_if_missing("events", "parent_event_id", "parent_event_id INTEGER")
        await add_if_missing("messages", "delivered_at", "delivered_at TEXT")
        # 旧 10軸採点ルーブリック (検閲官オウガイ) の廃止に伴う列削除
        await drop_if_present("revisions", "scores")

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
        async with self._connect() as db:
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
        async with self._connect() as db:
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
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_tasks(
        self,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        q: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status=?")
            params.append(status)
        if assigned_to:
            clauses.append("assigned_to=?")
            params.append(assigned_to)
        if q:
            clauses.append("(title LIKE ? OR description LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])
        if since:
            clauses.append("created_at>=?")
            params.append(since)
        if until:
            clauses.append("created_at<=?")
            params.append(until)
        sql = "SELECT * FROM tasks"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY created_at DESC"
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(sql, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    # --- subtasks ---
    async def create_subtask(
        self,
        parent_task_id: str,
        assigned_to: str,
        description: str,
        sub_id: Optional[str] = None,
    ) -> str:
        """sub_id を渡すと既存行があれば再利用 (revision サイクル)、無ければ
        その id で作成する。渡さなければ UUID を発番。"""
        sub_id = sub_id or _new_id()
        async with self._connect() as db:
            await db.execute(
                "INSERT OR IGNORE INTO subtasks (id, parent_task_id, assigned_to, "
                "description, status, created_at) VALUES (?,?,?,?,?,?)",
                (sub_id, parent_task_id, assigned_to, description, "in_progress", _now()),
            )
            await db.commit()
        return sub_id

    async def complete_subtask(self, sub_id: str, deliverable_path: Optional[str] = None) -> None:
        async with self._connect() as db:
            await db.execute(
                "UPDATE subtasks SET status='done', completed_at=?, deliverable_path=? WHERE id=?",
                (_now(), deliverable_path, sub_id),
            )
            await db.commit()

    async def list_subtasks(self, parent_task_id: str) -> list[dict[str, Any]]:
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM subtasks WHERE parent_task_id=? ORDER BY created_at",
                (parent_task_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def get_subtask_assignee(self, sub_id: str) -> Optional[str]:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT assigned_to FROM subtasks WHERE id=?", (sub_id,)
            )
            row = await cur.fetchone()
            return row[0] if row else None

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
        async with self._connect() as db:
            await db.execute(
                "INSERT INTO messages (id, task_id, from_agent, to_agent, content, "
                "message_type, timestamp) VALUES (?,?,?,?,?,?,?)",
                (msg_id, task_id, from_agent, to_agent, content, message_type, _now()),
            )
            await db.commit()
        return msg_id

    async def list_messages(self, task_id: str) -> list[dict[str, Any]]:
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM messages WHERE task_id=? ORDER BY timestamp", (task_id,)
            )
            return [dict(r) for r in await cur.fetchall()]

    async def list_messages_by_agent(
        self,
        agent: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """from_agent または to_agent が指定エージェントのメッセージを新→旧で limit 件。

        ピクセル UI のサイドパネル「過去のやり取り」で使用。
        """
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM messages WHERE from_agent=? OR to_agent=? "
                "ORDER BY timestamp DESC LIMIT ?",
                (agent, agent, int(limit)),
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
        async with self._connect() as db:
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
        async with self._connect() as db:
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
        async with self._connect() as db:
            await db.execute(
                "INSERT INTO revisions (id, task_id, subtask_id, round, evaluation, "
                "decision, created_at) VALUES (?,?,?,?,?,?,?)",
                (rev_id, task_id, subtask_id, round_, evaluation, decision, _now()),
            )
            await db.commit()
        return rev_id

    async def count_revisions(self, subtask_id: str) -> int:
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM revisions WHERE subtask_id=? AND decision='revise'",
                (subtask_id,),
            )
            (n,) = await cur.fetchone()
            return n

    async def list_revisions(self, task_id: str) -> list[dict[str, Any]]:
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM revisions WHERE task_id=? ORDER BY created_at",
                (task_id,),
            )
            return [dict(r) for r in await cur.fetchall()]

    async def count_agent_calls(self, task_id: str) -> int:
        """events テーブルから案件内のエージェント起動回数 (agent_start) を数える。"""
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM events WHERE task_id=? AND event_type='agent_start'",
                (task_id,),
            )
            (n,) = await cur.fetchone()
            return n

    async def count_consult_pair(self, task_id: str, from_agent: str, to_agent: str) -> int:
        """同一 (from→to) ペアの consult メッセージ件数。"""
        async with self._connect() as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM messages WHERE task_id=? AND from_agent=? "
                "AND to_agent=? AND message_type='consult'",
                (task_id, from_agent, to_agent),
            )
            (n,) = await cur.fetchone()
            return n

    # --- events ---
    async def list_events(
        self,
        task_id: Optional[str] = None,
        limit: int = 200,
        since_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if task_id is not None:
            clauses.append("task_id = ?")
            params.append(task_id)
        if since_id is not None:
            clauses.append("id > ?")
            params.append(since_id)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(int(limit))
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                f"SELECT id, timestamp, agent, event_type, task_id, details "
                f"FROM events {where} ORDER BY id DESC LIMIT ?",
                params,
            )
            rows = await cur.fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d["details"]) if d["details"] else {}
            except json.JSONDecodeError:
                d["details"] = {"raw": d["details"]}
            out.append(d)
        return out

    async def last_event_id(self) -> int:
        """events テーブルの最大 id (空なら 0)。pump タスクの起点用。"""
        async with self._connect() as db:
            cur = await db.execute("SELECT COALESCE(MAX(id), 0) FROM events")
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def log_event(
        self,
        agent: str,
        event_type: str,
        task_id: Optional[str],
        details: Optional[dict] = None,
        parent_event_id: Optional[int] = None,
    ) -> int:
        """events に 1 行追加し、insert された id を返す。"""
        async with self._connect() as db:
            cur = await db.execute(
                "INSERT INTO events (timestamp, agent, event_type, task_id, details, parent_event_id) "
                "VALUES (?,?,?,?,?,?)",
                (
                    _now(),
                    agent,
                    event_type,
                    task_id,
                    json.dumps(details or {}, ensure_ascii=False),
                    parent_event_id,
                ),
            )
            event_id = cur.lastrowid
            await db.commit()
            return int(event_id) if event_id is not None else 0

    # --- inbox-watcher 連携 ---
    async def fetch_undelivered_messages(self) -> list[dict[str, Any]]:
        """delivered_at が NULL のメッセージを古い順に取得。"""
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM messages WHERE delivered_at IS NULL ORDER BY timestamp"
            )
            return [dict(r) for r in await cur.fetchall()]

    async def mark_delivered(self, message_id: str) -> None:
        async with self._connect() as db:
            await db.execute(
                "UPDATE messages SET delivered_at=? WHERE id=?",
                (_now(), message_id),
            )
            await db.commit()

    async def find_reply(
        self,
        task_id: Optional[str],
        from_agent: str,
        to_agent: str,
        after_id: str,
        message_type: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """consult_souther の polling 用。after_id より新しい (from→to) のメッセージを 1 件返す。"""
        async with self._connect() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT timestamp FROM messages WHERE id=?", (after_id,))
            row = await cur.fetchone()
            after_ts = row[0] if row else "1970-01-01T00:00:00+00:00"

            clauses = ["from_agent=?", "to_agent=?", "id != ?", "timestamp > ?"]
            params: list[Any] = [from_agent, to_agent, after_id, after_ts]
            if task_id is not None:
                clauses.append("task_id=?")
                params.append(task_id)
            if message_type is not None:
                clauses.append("message_type=?")
                params.append(message_type)

            sql = (
                "SELECT * FROM messages WHERE "
                + " AND ".join(clauses)
                + " ORDER BY timestamp ASC LIMIT 1"
            )
            cur = await db.execute(sql, params)
            row = await cur.fetchone()
            return dict(row) if row else None


_store_singleton: Optional[Store] = None


def get_store() -> Store:
    global _store_singleton
    if _store_singleton is None:
        _store_singleton = Store()
    return _store_singleton
