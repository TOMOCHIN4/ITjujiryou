#!/usr/bin/env python3
"""IT十字陵 inbox watcher。

SQLite messages を 1 秒ごとに polling し、delivered_at が NULL の行を該当
エージェントの tmux pane に `tmux send-keys` で投入する。

Phase A は 2 エージェント (souther, yuko) のみ対応。Phase B で 5 人に拡張する。

pane の対応は環境変数で上書き可:
  ITJ_PANE_SOUTHER (default: itj:office.0)
  ITJ_PANE_YUKO    (default: itj:office.1)
  ...

注意: 現状は pane の idle 判定をしていない。Claude Code が他作業中の pane に
send-keys すると割り込むため、Phase A では「同時並行発注はしない」運用とする。
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.memory.store import get_store  # noqa: E402

POLL_INTERVAL = float(os.environ.get("ITJ_WATCHER_POLL_INTERVAL", "1.0"))

PANE_MAP = {
    "souther": os.environ.get("ITJ_PANE_SOUTHER", "itj:office.0"),
    "yuko": os.environ.get("ITJ_PANE_YUKO", "itj:office.1"),
    "designer": os.environ.get("ITJ_PANE_DESIGNER", ""),
    "engineer": os.environ.get("ITJ_PANE_ENGINEER", ""),
    "writer": os.environ.get("ITJ_PANE_WRITER", ""),
}


def _pane_for(agent: str) -> str:
    return PANE_MAP.get(agent, "")


def tmux_send(pane: str, text: str) -> None:
    """pane に文字列を流し込み Enter を打つ。

    long text を一発で送ると tmux の改行解釈で二度送信されることがあるため、
    `tmux load-buffer + paste-buffer` を使った方が安定。Phase A の prompt 規模
    (数百〜千文字程度) ではこの方式で問題ない経験則。
    """
    try:
        # buffer 経由で paste すると改行が保持される
        proc = subprocess.run(
            ["tmux", "load-buffer", "-"], input=text, text=True, check=False
        )
        if proc.returncode != 0:
            return
        subprocess.run(["tmux", "paste-buffer", "-d", "-t", pane], check=False)
        # Claude Code の prompt 入力を確定するため Enter を送る
        subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], check=False)
    except FileNotFoundError:
        # tmux 未起動 / 未インストール
        print("[watcher] tmux command not found", file=sys.stderr)


def format_prompt(msg: dict) -> str:
    content = msg["content"]
    task_id = msg.get("task_id") or ""
    return (
        f"新着メッセージ (msg_id={msg['id']}):\n"
        f"  from: {msg['from_agent']}\n"
        f"  type: {msg['message_type']}\n"
        f"  task_id: {task_id}\n"
        "---\n"
        f"{content}\n"
        "---\n"
        "このメッセージに対応してください。"
    )


async def main() -> None:
    store = get_store()
    await store.init()
    print(
        f"[watcher] start. poll={POLL_INTERVAL}s pane_map={ {k:v for k,v in PANE_MAP.items() if v} }"
    )
    while True:
        t0 = time.monotonic()
        try:
            msgs = await store.fetch_undelivered_messages()
        except Exception as e:  # noqa: BLE001
            print(f"[watcher] fetch error: {e}", file=sys.stderr)
            await asyncio.sleep(POLL_INTERVAL)
            continue

        for m in msgs:
            to = m["to_agent"]
            # client 宛は WS ダッシュボード経由で人間に見せる。watcher は配信スキップ
            if to == "client":
                await store.mark_delivered(m["id"])
                continue
            pane = _pane_for(to)
            if not pane:
                # 未配置の宛先 (Phase A では designer/engineer/writer は不在)
                print(
                    f"[watcher] no pane for {to}; leaving msg={m['id'][:8]} "
                    "(will be picked up after pane is added)"
                )
                continue
            prompt = format_prompt(m)
            tmux_send(pane, prompt)
            await store.mark_delivered(m["id"])
            print(
                f"[watcher] -> {to:<8s} ({m['message_type']:<16s}) msg={m['id'][:8]} pane={pane}"
            )

        elapsed = time.monotonic() - t0
        await asyncio.sleep(max(0.0, POLL_INTERVAL - elapsed))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[watcher] bye")
