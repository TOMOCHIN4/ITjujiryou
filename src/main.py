"""愛帝十字陵 CLI エントリポイント (マルチプロセス構成)。

使い方:
    python -m src.main init                          # DB 初期化
    python -m src.main cli                           # 発注を DB に投入する CLI
    python -m src.main serve [--host H] [--port P]   # Web ダッシュボード起動

注: マルチプロセス構成では、エージェントは ./scripts/start_office.sh で起動した
tmux session 内の Claude Code プロセス群が担う。本 CLI と Web ダッシュボードは
発注を SQLite に投入するだけで、応答は inbox_watcher 経由で tmux pane のユウコ
が生成する。
"""
from __future__ import annotations

import asyncio
import sys

for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="replace")

from src.memory.store import get_store


async def cmd_init() -> None:
    store = get_store()
    await store.init()
    print(f"DB 初期化完了: {store.db_path}")


async def cmd_cli() -> None:
    """発注を queue に投入する CLI (応答は tmux pane / Web ダッシュボード側で観る)。"""
    store = get_store()
    await store.init()

    print("=" * 60)
    print("愛帝十字陵 CLI 発注口")
    print("先に ./scripts/start_office.sh で事務所を起動しておいてください。")
    print("'exit' で終了。空行送信で確定。複数行入力可。")
    print("=" * 60)

    while True:
        print("\n[あなた]> ", end="", flush=True)
        lines: list[str] = []
        try:
            while True:
                line = input()
                if line.strip() == "":
                    if lines:
                        break
                    continue
                lines.append(line)
        except EOFError:
            print("\n終了します。")
            return

        text = "\n".join(lines).strip()
        if text.lower() == "exit":
            print("終了します。")
            return
        if not text:
            continue

        title = text.splitlines()[0][:60] or "(無題)"
        task_id = await store.create_task(
            title=title, description=text, client_request=text
        )
        msg_id = await store.add_message("client", "yuko", text, "email", task_id)
        await store.log_event(
            "client",
            "order_queued",
            task_id,
            details={"msg_id": msg_id, "preview": text[:120]},
        )
        print(f"[queue] task_id={task_id}  msg_id={msg_id[:8]}")
        print("ユウコの応答は tmux session 'itj' または http://localhost:8000 で確認してください。")


async def cmd_serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    await get_store().init()
    import uvicorn
    from src.ui.api import app

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    print(f"愛帝十字陵 ダッシュボード起動: http://{host}:{port}")
    await server.serve()


def _parse_serve_args(argv: list[str]) -> tuple[str, int]:
    host = "127.0.0.1"
    port = 8000
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--host" and i + 1 < len(argv):
            host = argv[i + 1]
            i += 2
        elif a == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1])
            i += 2
        else:
            i += 1
    return host, port


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "init":
        asyncio.run(cmd_init())
    elif cmd == "cli":
        asyncio.run(cmd_cli())
    elif cmd == "serve":
        host, port = _parse_serve_args(sys.argv[2:])
        asyncio.run(cmd_serve(host, port))
    else:
        print(f"不明なコマンド: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
