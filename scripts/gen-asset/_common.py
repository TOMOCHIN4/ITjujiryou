# >>> Claude Code Init >>>
"""アセット生成スクリプト共通関数。"""

import os
import re
import sys
import subprocess
from pathlib import Path


def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.stderr.write(
            "✗ GEMINI_API_KEY が未設定です。\n"
            "  env/env.md に GEMINI_API_KEY=<key> を追加し、\n"
            "  set -a && . env/env.md && set +a でロード、\n"
            "  または export GEMINI_API_KEY=...\n"
            "  取得：https://aistudio.google.com/apikey\n"
        )
        sys.exit(2)
    if not re.match(r"^AIza[0-9A-Za-z_\-]{35}$", key):
        sys.stderr.write("△ GEMINI_API_KEY の形式が想定と異なります。\n")
    return key


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        )
        return Path(out.decode().strip()).resolve()
    except Exception:
        return Path.cwd().resolve()


def resolve_output(arg, default_relative: str) -> Path:
    if arg is None:
        return project_root() / default_relative
    p = Path(arg)
    return p if p.is_absolute() else project_root() / p


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def slugify(text: str, fallback: str = "asset") -> str:
    s = re.sub(r"[^\w\-_.]", "_", text.strip())[:60]
    return s or fallback
# <<< Claude Code Init <<<
