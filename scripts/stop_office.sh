#!/usr/bin/env bash
# IT十字陵 tmux セッション停止
set -euo pipefail
SESSION="${ITJ_SESSION:-itj}"
if tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux kill-session -t "$SESSION"
    echo "[stop_office] killed session '$SESSION'"
else
    echo "[stop_office] no session '$SESSION'"
fi
