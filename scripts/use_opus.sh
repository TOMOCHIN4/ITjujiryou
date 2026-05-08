#!/usr/bin/env bash
# 5 人全員を本番 Opus に戻す (settings.local.json を削除)。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

removed=0
for ws in "$ROOT"/workspaces/*/; do
    role=$(basename "$ws")
    target="${ws}.claude/settings.local.json"
    if [ -f "$target" ]; then
        rm -f "$target"
        echo "[$role] removed override -> default Opus (settings.json)"
        removed=$((removed + 1))
    fi
done

if [ "$removed" -eq 0 ]; then
    echo "settings.local.json は存在しません (既に Opus デフォルト)。"
fi
