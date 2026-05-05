"""イベントブローカ。logger からの publish を WS 購読者にファンアウトする。

logger を import しないこと（循環回避）。
"""
from __future__ import annotations

import asyncio
from typing import Any


class EventBroker:
    def __init__(self, queue_max: int = 1000) -> None:
        self._subs: set[asyncio.Queue] = set()
        self._queue_max = queue_max

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._queue_max)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def publish(self, payload: dict[str, Any]) -> None:
        for q in list(self._subs):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # 古い event の遅延より生存性優先
                pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subs)


broker = EventBroker()
