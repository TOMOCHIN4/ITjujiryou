"""IT十字陵 CLI エントリポイント。

使い方:
    python -m src.main init                          # DB 初期化
    python -m src.main cli                           # 対話モードで発注
    python -m src.main serve [--host H] [--port P]   # Web ダッシュボード起動
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
    # 起動時に DB を確実に用意
    await get_store().init()
    # 遅延 import (claude-agent-sdk が無くても init は通したいため)
    from src.reception import handle_client_message

    print("=" * 60)
    print("IT十字陵 受付窓口 — 営業主任ユウコがご対応します。")
    print("発注内容を入力してください。'exit' で終了、'new' で新規案件、")
    print("空行送信で確定。複数行入力可。")
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

        print("\n--- 事務所内タイムライン ---")
        try:
            response = await handle_client_message(text)
        except Exception as e:
            print(f"\n[エラー] {type(e).__name__}: {e}")
            continue
        print("--- /タイムライン ---\n")
        print(f"[ユウコ]\n{response}\n")


async def cmd_serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    await get_store().init()
    import uvicorn
    from src.ui.api import app

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    print(f"IT十字陵 ダッシュボード起動: http://{host}:{port}")
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
