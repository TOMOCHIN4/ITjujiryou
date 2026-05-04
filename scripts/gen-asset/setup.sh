#!/usr/bin/env bash
# >>> Claude Code Init >>>
set -euo pipefail
cd "$(dirname "$0")"

# Python 3.10+ が必要（google-genai の image_size など新フィールドのため）
PY=""
for v in python3.13 python3.12 python3.11 python3.10; do
  if command -v "$v" >/dev/null 2>&1; then PY="$v"; break; fi
done
if [ -z "$PY" ]; then
  if command -v python3 >/dev/null 2>&1; then
    MAJOR_MINOR=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    case "$MAJOR_MINOR" in
      3.10|3.11|3.12|3.13|3.14) PY=python3 ;;
    esac
  fi
fi
if [ -z "$PY" ]; then
  echo "✗ Python 3.10+ が必要です（python3.9 は EOL で google-genai が 4K 非対応）"
  echo "  brew install python@3.12 などで導入してください。"
  exit 1
fi
echo "==> Using $PY ($($PY --version))"

if [ ! -d venv ]; then
  "$PY" -m venv venv
  echo "✓ venv 作成 ($PY)"
fi

. venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "△ ffmpeg 未インストール（brew install ffmpeg）"
fi

echo "✓ scripts/gen-asset セットアップ完了"

# .env の GEMINI_API_KEY を確認（IT十字陵プロジェクトルート想定）
ENV_FILE="$(cd ../.. && pwd)/.env"
if [ -f "$ENV_FILE" ] && grep -q "^GEMINI_API_KEY=" "$ENV_FILE" 2>/dev/null; then
  echo "✓ $ENV_FILE に GEMINI_API_KEY 設定済み"
else
  echo "△ .env に GEMINI_API_KEY が見当たりません"
  echo "  echo 'export GEMINI_API_KEY=...' >> .env"
  echo "  IOS_app プロジェクトの env/env.md からコピーできます"
fi
# <<< Claude Code Init <<<
