#!/usr/bin/env bash
# 5 人全員を Haiku モードに切り替える (接続検証・節約モード)。
#
# 各 workspace の .claude/settings.local.json で model だけ上書き。
# settings.local.json は .gitignore 済みなので残骸は git に紛れない。
#
# 引数で別モデルを指定可。例:
#   ./scripts/use_haiku.sh                                  # Haiku 4.5
#   ./scripts/use_haiku.sh claude-sonnet-4-6                # Sonnet 4.6
#   ./scripts/use_haiku.sh claude-opus-4-7                  # Opus 4.7 (use_opus と同じ効果)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL="${1:-claude-haiku-4-5-20251001}"

for ws in "$ROOT"/workspaces/*/; do
    role=$(basename "$ws")
    target="${ws}.claude/settings.local.json"
    cat > "$target" <<JSON
{
  "model": "$MODEL"
}
JSON
    echo "[$role] model -> $MODEL  ($target)"
done

cat <<EOM

完了。次回 ./scripts/start_office.sh 起動時から $MODEL が使われます。
本番に戻すときは: ./scripts/use_opus.sh
EOM
