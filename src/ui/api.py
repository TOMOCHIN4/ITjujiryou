"""FastAPI ダッシュボード。Phase 1 の reception/store/logger を薄くラップする。"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.memory.store import get_store
from src.ui.broker import broker

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
OUTPUTS_DIR = REPO_ROOT / "outputs"

STAFF = ["souther", "yuko", "designer", "engineer", "writer"]
WORKING_WINDOW_SEC = 30  # 直近イベントから何秒以内なら working とみなすか


app = FastAPI(title="IT十字陵 Dashboard", version="0.2.0")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/tasks")
async def api_list_tasks(status: Optional[str] = None) -> list[dict[str, Any]]:
    return await get_store().list_tasks(status=status)


@app.get("/api/tasks/{task_id}")
async def api_task_detail(task_id: str) -> dict[str, Any]:
    store = get_store()
    task = await store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    subtasks = await store.list_subtasks(task_id)
    messages = await store.list_messages(task_id)
    deliverables = await _list_deliverables(task_id)
    return {
        "task": task,
        "subtasks": subtasks,
        "messages": messages,
        "deliverables": deliverables,
    }


async def _list_deliverables(task_id: str) -> list[dict[str, Any]]:
    import aiosqlite

    store = get_store()
    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT id, file_path, file_type, created_by, description, created_at "
            "FROM deliverables WHERE task_id=? ORDER BY created_at",
            (task_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


@app.get("/api/events")
async def api_list_events(
    task_id: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
    since_id: Optional[int] = None,
) -> list[dict[str, Any]]:
    return await get_store().list_events(task_id=task_id, limit=limit, since_id=since_id)


@app.get("/api/staff")
async def api_staff() -> list[dict[str, Any]]:
    """5 名の直近イベントから state (idle / working) を派生。"""
    events = await get_store().list_events(limit=200)
    now = datetime.now(timezone.utc)
    by_agent: dict[str, dict[str, Any]] = {}
    for ev in events:
        a = ev.get("agent")
        if a not in STAFF:
            continue
        if a in by_agent:
            continue
        by_agent[a] = ev

    out: list[dict[str, Any]] = []
    for name in STAFF:
        latest = by_agent.get(name)
        state = "idle"
        if latest:
            try:
                ts = datetime.fromisoformat(latest["timestamp"])
                if (now - ts).total_seconds() <= WORKING_WINDOW_SEC:
                    state = "working"
            except (ValueError, TypeError):
                pass
        out.append({
            "agent": name,
            "state": state,
            "latest_event": latest,
        })
    return out


class OrderRequest(BaseModel):
    text: str
    task_id: Optional[str] = None


@app.post("/api/orders")
async def api_post_order(req: OrderRequest) -> dict[str, Any]:
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    # 遅延 import（claude-agent-sdk 起動を REST 解決まで遅らせる）
    from src.reception import handle_client_message

    response = await handle_client_message(text, task_id=req.task_id)
    # 直近に作成された task_id を返す。reception 側で task が必ず確定する。
    # 簡便に最新 1 件を引いて返す（同時並行発注は Phase 2.x 以降で扱う）。
    tasks = await get_store().list_tasks()
    task_id = tasks[0]["id"] if tasks else None
    return {"task_id": task_id, "response": response}


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    await websocket.accept()
    # 接続直後にスナップショット (新しい順 100 件 → 古→新で送る)
    snapshot = await get_store().list_events(limit=100)
    for ev in reversed(snapshot):
        await websocket.send_json({"type": "event", **_event_to_payload(ev)})

    queue = await broker.subscribe()
    try:
        while True:
            payload = await queue.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        broker.unsubscribe(queue)


def _event_to_payload(ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": ev.get("id"),
        "timestamp": ev.get("timestamp"),
        "agent": ev.get("agent"),
        "event_type": ev.get("event_type"),
        "task_id": ev.get("task_id"),
        "details": ev.get("details") or {},
    }


# 静的マウント (404 を返さないよう、ディレクトリが無くても作っておく)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


@app.exception_handler(Exception)
async def _generic_handler(_, exc: Exception) -> JSONResponse:  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=500, content={"error": f"{type(exc).__name__}: {exc}"})
