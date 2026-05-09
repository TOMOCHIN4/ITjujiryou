"""FastAPI ダッシュボード。Phase 1 の reception/store/logger を薄くラップする。"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

from src.memory.store import get_store
from src.ui.broker import broker

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
PIXEL_DIR = STATIC_DIR / "pixel"
OUTPUTS_DIR = REPO_ROOT / "outputs"

STAFF = ["souther", "yuko", "designer", "engineer", "writer"]
WORKING_WINDOW_SEC = 30  # 直近イベントから何秒以内なら working とみなすか


app = FastAPI(title="愛帝十字陵 Dashboard", version="0.3.0")


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    """開発時に /pixel-static, /static, /outputs のブラウザキャッシュを無効化。
    ES module / 画像を編集→リロードで即反映するため。"""

    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        path = request.url.path
        if path.startswith(("/pixel-static", "/static", "/outputs")):
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
        return resp


app.add_middleware(NoCacheStaticMiddleware)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/tasks")
async def api_list_tasks(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    q: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> list[dict[str, Any]]:
    return await get_store().list_tasks(
        status=status,
        assigned_to=assigned_to,
        q=q,
        since=since,
        until=until,
    )


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


@app.get("/pixel")
@app.get("/pixel/")
async def pixel_index() -> FileResponse:
    """事務所俯瞰ピクセル UI のエントリポイント (Phase 1)。"""
    return FileResponse(PIXEL_DIR / "index.html")


@app.get("/api/staff/{agent}/profile")
async def api_staff_profile(agent: str) -> dict[str, Any]:
    """ピクセル UI のサイドパネル用。担当中タスク + 直近メッセージ + 最新自発イベントを返す。"""
    if agent not in STAFF:
        raise HTTPException(status_code=404, detail="unknown agent")
    store = get_store()
    all_assigned = await store.list_tasks(assigned_to=agent)
    active_tasks = [t for t in all_assigned if t.get("status") != "delivered"]
    recent_messages = await store.list_messages_by_agent(agent, limit=20)
    events = await store.list_events(limit=200)
    latest_self_event = next((e for e in events if e.get("agent") == agent), None)
    return {
        "agent": agent,
        "active_tasks": active_tasks,
        "recent_messages": recent_messages,
        "latest_event": latest_self_event,
    }


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
    """マルチプロセス構成では DB に投入して即 return する。
    ユウコ pane は inbox_watcher 経由で起動され、応答は WS /ws/events で配信される。
    """
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    store = get_store()
    if req.task_id:
        task = await store.get_task(req.task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"task {req.task_id} not found")
        task_id = req.task_id
    else:
        title = text.splitlines()[0][:60] or "(無題)"
        task_id = await store.create_task(
            title=title,
            description=text,
            client_request=text,
        )

    msg_id = await store.add_message("client", "yuko", text, "email", task_id)
    await store.log_event(
        "client",
        "order_queued",
        task_id,
        details={"msg_id": msg_id, "preview": text[:120]},
    )
    return {
        "task_id": task_id,
        "msg_id": msg_id,
        "status": "queued",
        "note": "ユウコの応答は /ws/events か /api/tasks/{task_id} で取得してください。",
    }


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
PIXEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/pixel-static", StaticFiles(directory=PIXEL_DIR), name="pixel-static")
app.mount("/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")


@app.exception_handler(Exception)
async def _generic_handler(_, exc: Exception) -> JSONResponse:  # type: ignore[no-untyped-def]
    return JSONResponse(status_code=500, content={"error": f"{type(exc).__name__}: {exc}"})
