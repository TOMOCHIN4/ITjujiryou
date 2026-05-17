#!/usr/bin/env python3
"""`.claude/phase_state.json` を **初回 Phase 用** に初期化する helper。

天翔十字フローの `/init-plan` skill から呼ばれる、初回 Phase 専用 helper。
2 回目以降の Phase 着手は `advance_phase_state.py` を使うこと。

受理キー (whitelist): phase_current / phase_simple_goal / phase_total /
                     phase_remaining / latest_plan_path
ガード:
  - 既存 phase_state.json の phase_current が "_frozen" 以外なら exit 1
    (= 進行中フローを潰さないため、init は凍結状態からのみ実行可)
  - phase_total / phase_remaining は int 化

将来 phase_state.json スキーマを拡張するときは、追加キーが mutable か
immutable かを判定し、本 helper の `ACCEPTED` と
`advance_phase_state.py` の `ALLOWED` / `IMMUTABLE` を整合的に更新する。

使用例:
  python3 scripts/dev_hooks/init_phase_state.py \\
    phase_current=A \\
    phase_simple_goal="..." \\
    phase_total=3 \\
    phase_remaining=2 \\
    latest_plan_path=.claude/plans/phase_A.md
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
ACCEPTED = {
    "phase_current",
    "phase_simple_goal",
    "phase_total",
    "phase_remaining",
    "latest_plan_path",
}
INT_KEYS = {"phase_total", "phase_remaining"}
REQUIRED_KEYS = ACCEPTED | {"updated_at"}


def _find_phase_state() -> Path:
    env = os.environ.get("ITJ_PHASE_STATE_PATH")
    if env:
        p = Path(env).resolve()
        if not p.is_file():
            raise FileNotFoundError(
                f"ITJ_PHASE_STATE_PATH={env} のファイルが存在しません"
            )
        return p
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


def _atomic_write(state_path: Path, state: dict) -> None:
    fd, tmp_path = tempfile.mkstemp(
        prefix=".phase_state.", suffix=".json", dir=str(state_path.parent)
    )
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp_path, state_path)


def main(argv: list[str]) -> int:
    try:
        diff = _parse_kv(argv)
    except ValueError as exc:
        print(f"init_phase_state: {exc}", file=sys.stderr)
        return 1

    bad = set(diff) - ACCEPTED
    if bad:
        print(
            f"init_phase_state: 受理しないキーが渡されました: {sorted(bad)} "
            f"(受理キーは {sorted(ACCEPTED)})",
            file=sys.stderr,
        )
        return 1

    try:
        state_path = _find_phase_state()
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"init_phase_state: 読込失敗: {exc}", file=sys.stderr)
        return 1

    if state.get("phase_current") != "_frozen":
        print(
            f"init_phase_state: 既存 phase_current={state.get('phase_current')!r} は "
            f'"_frozen" ではありません。進行中フローは init で潰せません。'
            "2 回目以降の Phase 着手は advance_phase_state.py を使ってください。",
            file=sys.stderr,
        )
        return 1

    state.update(diff)
    state["updated_at"] = datetime.now(JST).isoformat(timespec="seconds")

    missing = REQUIRED_KEYS - set(state.keys())
    if missing:
        print(
            f"init_phase_state: 必須キーが欠落: {sorted(missing)}", file=sys.stderr
        )
        return 1

    try:
        _atomic_write(state_path, state)
    except Exception as exc:
        print(f"init_phase_state: 書込失敗: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
