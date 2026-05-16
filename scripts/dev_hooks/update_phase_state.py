#!/usr/bin/env python3
"""`.claude/phase_state.json` を atomic に更新する helper。

天翔十字フローの skill (`/init-plan` / `/next-plan`) から呼び出される。
任意の key=value を CLI 引数で渡し、`updated_at` は自動で JST 現在時刻に置換する。

使用例:
  python3 scripts/dev_hooks/update_phase_state.py \
    sub_step_current=0-3 \
    sub_step_remaining=0 \
    latest_plan_path=.claude/plans/phase_0_plan_v3.md

挙動:
  1. 現 phase_state.json を読み込み JSON として parse
  2. 引数で渡された key=value を適用 (int 化は phase_total_steps / sub_step_remaining のみ)
  3. updated_at を JST ISO 8601 (秒精度) で置換
  4. temp file に書き → os.replace() で atomic rename
  5. 失敗時は stderr に短文 + exit 1
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
INT_KEYS = {"phase_total_steps", "sub_step_remaining"}
REQUIRED_KEYS = {
    "phase",
    "phase_simple_goal",
    "phase_total_steps",
    "sub_step_current",
    "sub_step_remaining",
    "latest_plan_path",
    "updated_at",
}


def _find_phase_state() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / ".claude" / "phase_state.json"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(".claude/phase_state.json が見つかりません")


def _parse_kv(args: list[str]) -> dict:
    out: dict = {}
    for token in args:
        if "=" not in token:
            raise ValueError(f"key=value 形式ではありません: {token!r}")
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in INT_KEYS:
            try:
                out[key] = int(value)
            except ValueError as exc:
                raise ValueError(f"{key} は整数で渡してください: {value!r}") from exc
        else:
            out[key] = value
    return out


def main(argv: list[str]) -> int:
    try:
        diff = _parse_kv(argv)
    except ValueError as exc:
        print(f"update_phase_state: {exc}", file=sys.stderr)
        return 1

    try:
        state_path = _find_phase_state()
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"update_phase_state: 読込失敗: {exc}", file=sys.stderr)
        return 1

    state.update(diff)
    state["updated_at"] = datetime.now(JST).isoformat(timespec="seconds")

    missing = REQUIRED_KEYS - set(state.keys())
    if missing:
        print(
            f"update_phase_state: 必須キーが欠落: {sorted(missing)}", file=sys.stderr
        )
        return 1

    try:
        fd, tmp_path = tempfile.mkstemp(
            prefix=".phase_state.", suffix=".json", dir=str(state_path.parent)
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp_path, state_path)
    except Exception as exc:
        print(f"update_phase_state: 書込失敗: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
