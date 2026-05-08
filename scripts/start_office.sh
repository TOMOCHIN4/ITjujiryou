#!/usr/bin/env bash
# IT十字陵 マルチプロセス起動スクリプト (Phase A: 2 pane = souther + yuko)
#
# tmux session "itj" を立て:
#   window "office": pane 0=souther, pane 1=yuko, pane 2=monitor (timeline tail)
#   window "watcher": inbox_watcher.py
#   window "api":     FastAPI (Phase 2.x ダッシュボード)
#
# 既にセッションがあれば attach のみ。
# 環境変数:
#   ITJ_SKIP_PERMISSIONS=true (default) : claude を --dangerously-skip-permissions で起動
#   ITJ_OPEN_API=true (default)         : api ウィンドウを起動
#   ITJ_OPEN_WATCHER=true (default)     : watcher ウィンドウを起動

set -euo pipefail

SESSION="${ITJ_SESSION:-itj}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "[start_office] session '$SESSION' は既に存在します。"
    echo "  attach: tmux attach -t $SESSION"
    echo "  kill:   $ROOT/scripts/stop_office.sh"
    exit 0
fi

mkdir -p "$ROOT/data/logs"
: > /dev/null  # ensure timeline.log exists
touch "$ROOT/data/logs/timeline.log"

# ───────── DB の WAL モード化 + マイグレーション ─────────
"$ROOT/.venv/bin/python" -c "
import asyncio
from src.memory.store import get_store
asyncio.run(get_store().init())
print('[start_office] DB initialized (WAL mode)')
" 2>&1 | grep -v '^$' || true

CLAUDE_CMD="claude"
if [ "${ITJ_SKIP_PERMISSIONS:-true}" = "true" ]; then
    CLAUDE_CMD="claude --dangerously-skip-permissions"
fi
# claude が exit しても pane が消えないように bash を後追いで残す
WRAPPED_CLAUDE="$CLAUDE_CMD; echo '[claude exited, press Ctrl-C to leave bash]'; exec bash -i"

# ───────── window: office (3 pane) ─────────
tmux new-session  -d -s "$SESSION" -n office -c "$ROOT/workspaces/souther" \
    "bash -lc \"$WRAPPED_CLAUDE\""
sleep 0.4
tmux split-window -t "$SESSION:office"  -h -c "$ROOT/workspaces/yuko" \
    "bash -lc \"$WRAPPED_CLAUDE\""
sleep 0.4
tmux split-window -t "$SESSION:office"  -v -c "$ROOT" \
    "tail -F $ROOT/data/logs/timeline.log"

tmux select-layout -t "$SESSION:office" tiled
# pane タイトル設定 (tmux >= 2.6)
tmux select-pane -t "$SESSION:office.0" -T "souther"
tmux select-pane -t "$SESSION:office.1" -T "yuko"
tmux select-pane -t "$SESSION:office.2" -T "monitor"
tmux set-option -t "$SESSION:office" pane-border-status top || true

# ───────── window: watcher ─────────
if [ "${ITJ_OPEN_WATCHER:-true}" = "true" ]; then
    tmux new-window -t "$SESSION" -n watcher -c "$ROOT" \
        "$ROOT/.venv/bin/python $ROOT/scripts/inbox_watcher.py"
fi

# ───────── window: api ─────────
if [ "${ITJ_OPEN_API:-true}" = "true" ]; then
    tmux new-window -t "$SESSION" -n api -c "$ROOT" \
        "$ROOT/.venv/bin/python -m src.main serve"
fi

tmux select-window -t "$SESSION:office"

cat <<EOM
[start_office] session '$SESSION' を起動しました。

  - office  pane: 0=souther / 1=yuko / 2=monitor
  - watcher ウィンドウ: inbox_watcher.py 常駐
  - api     ウィンドウ: FastAPI ダッシュボード (http://localhost:8000)

  attach: tmux attach -t $SESSION
  stop  : $ROOT/scripts/stop_office.sh
EOM

if [ -t 0 ] && [ "${ITJ_AUTOATTACH:-true}" = "true" ]; then
    exec tmux attach -t "$SESSION"
fi
