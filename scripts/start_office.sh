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
#   ITJ_PERMISSION_MODE=auto (default、2026-05-14 切替) : claude を --permission-mode <mode> で起動
#       auto              : classifier が背景で危険操作を判定 (Max + Opus 4.7 要件)、`Tool(//abs/**)` path glob の実装不整合を回避できる現行推奨モード
#       dontAsk           : allow に列挙されたツール + read-only Bash のみ実行可、それ以外 auto-deny (旧推奨、path glob 不整合で本体/subagent ともに正しく動かない事例あり、memory: feedback_subagent_write_glob_inheritance.md)
#       bypassPermissions : --dangerously-skip-permissions 相当 (旧設定、permissions が全 skip される)
#       default           : 通常モード (プロンプトが出るので自律駆動不可)
#   ITJ_OPEN_API=true (default)           : api ウィンドウを起動
#   ITJ_OPEN_WATCHER=true (default)       : watcher ウィンドウを起動

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

PERMISSION_MODE="${ITJ_PERMISSION_MODE:-auto}"
case "$PERMISSION_MODE" in
    dontAsk|bypassPermissions|auto|default|acceptEdits|plan)
        CLAUDE_CMD="claude --permission-mode $PERMISSION_MODE"
        ;;
    *)
        echo "[start_office] unknown ITJ_PERMISSION_MODE='$PERMISSION_MODE' (allowed: dontAsk / bypassPermissions / auto / default / acceptEdits / plan)" >&2
        exit 1
        ;;
esac
# claude が exit しても pane が消えないように bash を後追いで残す
WRAPPED_CLAUDE="$CLAUDE_CMD; echo '[claude exited, press Ctrl-C to leave bash]'; exec bash -i"

# ───────── window: office (5 claude pane + monitor) ─────────
tmux new-session  -d -s "$SESSION" -n office -c "$ROOT/workspaces/souther" \
    "bash -lc \"$WRAPPED_CLAUDE\""
sleep 0.4
tmux split-window -t "$SESSION:office"  -h -c "$ROOT/workspaces/yuko" \
    "bash -lc \"$WRAPPED_CLAUDE\""
sleep 0.4
tmux split-window -t "$SESSION:office"  -h -c "$ROOT/workspaces/designer" \
    "bash -lc \"$WRAPPED_CLAUDE\""
sleep 0.4
tmux split-window -t "$SESSION:office"  -v -c "$ROOT/workspaces/engineer" \
    "bash -lc \"$WRAPPED_CLAUDE\""
sleep 0.4
tmux split-window -t "$SESSION:office"  -v -c "$ROOT/workspaces/writer" \
    "bash -lc \"$WRAPPED_CLAUDE\""
sleep 0.4
tmux split-window -t "$SESSION:office"  -v -c "$ROOT" \
    "tail -F $ROOT/data/logs/timeline.log"

tmux select-layout -t "$SESSION:office" tiled
# pane タイトル (tmux >= 2.6)
tmux select-pane -t "$SESSION:office.0" -T "souther"
tmux select-pane -t "$SESSION:office.1" -T "yuko"
tmux select-pane -t "$SESSION:office.2" -T "designer"
tmux select-pane -t "$SESSION:office.3" -T "engineer"
tmux select-pane -t "$SESSION:office.4" -T "writer"
tmux select-pane -t "$SESSION:office.5" -T "monitor"
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
[start_office] session '$SESSION' を起動しました (permission-mode=$PERMISSION_MODE)。

  - office  pane: 0=souther / 1=yuko / 2=designer / 3=engineer / 4=writer / 5=monitor
  - watcher ウィンドウ: inbox_watcher.py 常駐
  - api     ウィンドウ: FastAPI ダッシュボード (http://localhost:8000)

  attach: tmux attach -t $SESSION
  stop  : $ROOT/scripts/stop_office.sh
  Mode   : ITJ_PERMISSION_MODE=<mode> を環境変数で渡すと起動モードを切替 (デフォルト auto、2026-05-14 切替)
EOM

if [ -t 0 ] && [ "${ITJ_AUTOATTACH:-true}" = "true" ]; then
    exec tmux attach -t "$SESSION"
fi
