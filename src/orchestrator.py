"""社内ディスパッチの薄いラッパ。reception 経由でユウコを起動する。

ユウコは案件の起点であり call_chain depth=0 として登録する。
"""
from __future__ import annotations

from src.agents.base import run_agent
from src.tools.registry import get_mcp_server, push_call


async def run_yuko(user_message: str, task_id: str | None = None) -> str:
    async with push_call("yuko"):
        return await run_agent("yuko", user_message, get_mcp_server(), task_id=task_id)
