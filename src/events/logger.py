"""タイムラインログ。stdout と data/logs/timeline.log に出力し、DB にも記録する。"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.memory.store import get_store

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs" / "timeline.log"

AGENT_ICON = {
    "client": "📩",
    "yuko": "💼",
    "souther": "👑",
    "designer": "🎨",
    "engineer": "🛠",
    "writer": "✍️ ",
    "system": "⚙️ ",
}


def _log_path() -> Path:
    p = Path(os.environ.get("ITJUJIRYOU_LOG_PATH", DEFAULT_LOG_PATH))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _format_line(agent: str, message: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    icon = AGENT_ICON.get(agent, "•")
    return f"[{ts}] {icon} {agent}: {message}"


async def log(
    agent: str,
    message: str,
    *,
    event_type: str = "message",
    task_id: Optional[str] = None,
    details: Optional[dict] = None,
    print_stdout: bool = True,
) -> None:
    line = _format_line(agent, message)
    if print_stdout:
        print(line, flush=True)
    log_file = _log_path()
    with log_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    payload = {"message": message}
    if details:
        payload.update(details)
    await get_store().log_event(agent, event_type, task_id, payload)
    # WS ブローカへの publish (UI 未起動でも CLI を壊さない)
    try:
        from src.ui.broker import broker
        broker.publish({
            "type": "event",
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "event_type": event_type,
            "task_id": task_id,
            "details": payload,
        })
    except Exception:
        pass
