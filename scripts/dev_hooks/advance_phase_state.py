#!/usr/bin/env python3
"""`.claude/phase_state.json` を **2 回目以降の Phase 着手用** に遷移させる helper。

天翔十字フローの `/next-plan` skill から呼ばれる、遷移専用 helper。
初回 Phase 着手は `init_phase_state.py` を使うこと。

物理ガードの本質:
  - ALLOWED whitelist に **`phase_simple_goal` / `phase_total` を入れない**
    ことで、不変キー上書きの経路を物理的に存在させない。
  - 書込前に「new[immutable] == old[immutable]」を if 文で再確認
    (assert は `-O` で消えるため使わない)。

受理キー (whitelist): phase_current / phase_remaining / latest_plan_path
拒否キー (IMMUTABLE): phase_simple_goal / phase_total
ガード:
  - 既存 phase_current が None / "_frozen" なら exit 1 (= init から始めよ)
  - 既存 phase_remaining == 0 (= フロー完了済) なら exit 1
    (= freeze してから init し直せ。phase_total を暗黙に書き換える経路を塞ぐ)
  - 受理外のキーが 1 つでも渡されたら exit 1
  - 書込前に不変キー (simple_goal / total) が変わっていないことを再確認

将来 phase_state.json スキーマを拡張するときは、追加キーが mutable か
immutable かを判定して `ALLOWED` / `IMMUTABLE` を整合的に更新する
(`init_phase_state.py` の `ACCEPTED` も同期更新)。

使用例:
  python3 scripts/dev_hooks/advance_phase_state.py \\
    phase_current=B \\
    phase_remaining=1 \\
    latest_plan_path=.claude/plans/phase_B.md
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
ALLOWED = {"phase_current", "phase_remaining", "latest_plan_path"}
INT_KEYS = {"phase_remaining"}
IMMUTABLE = {"phase_simple_goal", "phase_total"}


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
        print(f"advance_phase_state: {exc}", file=sys.stderr)
        return 1

    bad = set(diff) - ALLOWED
    if bad:
        immutable_violation = bad & IMMUTABLE
        if immutable_violation:
            print(
                f"advance_phase_state: 不変キーへの書込試行: "
                f"{sorted(immutable_violation)}。"
                "シンプルゴール / 全 Phase 数 N は初回 init_phase_state.py 以降、"
                "書き換え不可です。",
                file=sys.stderr,
            )
        else:
            print(
                f"advance_phase_state: 受理しないキーが渡されました: {sorted(bad)} "
                f"(受理キーは {sorted(ALLOWED)})",
                file=sys.stderr,
            )
        return 1

    try:
        state_path = _find_phase_state()
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"advance_phase_state: 読込失敗: {exc}", file=sys.stderr)
        return 1

    if state.get("phase_current") in (None, "_frozen"):
        print(
            f"advance_phase_state: 既存 phase_current="
            f"{state.get('phase_current')!r} は進行中フローではありません。"
            "初回 Phase 着手は init_phase_state.py を使ってください。",
            file=sys.stderr,
        )
        return 1

    if state.get("phase_remaining") == 0:
        print(
            "advance_phase_state: 既存 phase_remaining=0 (= フロー完了済) の状態 "
            "では遷移できません。phase_total を超える Phase の追加と等価のため拒否します。"
            "新案件は freeze_phase_state.py --freeze でフローを凍結し、"
            "init_phase_state.py で立ち上げ直してください。",
            file=sys.stderr,
        )
        return 1

    new_state = {**state, **diff}

    for k in IMMUTABLE:
        if new_state.get(k) != state.get(k):
            print(
                f"advance_phase_state: 不変式違反: {k} が変化しました "
                f"({state.get(k)!r} → {new_state.get(k)!r})",
                file=sys.stderr,
            )
            return 1

    new_state["updated_at"] = datetime.now(JST).isoformat(timespec="seconds")

    try:
        _atomic_write(state_path, new_state)
    except Exception as exc:
        print(f"advance_phase_state: 書込失敗: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(new_state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
