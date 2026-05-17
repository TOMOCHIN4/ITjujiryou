#!/usr/bin/env python3
"""`.claude/phase_state.json` をフロー外作業のために凍結 / 復帰する helper。

天翔十字フロー本体・skill・hook・settings の改修中、または検証用に
フロー外作業に出るときに使う。`docs/development_layer_rules.md §3.4` 参照。

サブコマンド:
  --freeze              : phase_current="_frozen" を立て、不変キーをリセット
  --unfreeze-to-init    : 空白化し、次の `/init-plan` で再入力できる状態にする
                         (= phase_current="_frozen" のまま、unfrozen 後初回 Phase
                         を init から始めることを前提)

凍結中は UserPromptSubmit hook (`inject_phase.py`) が Phase 情報の
context 注入をスキップする。

使用例:
  python3 scripts/dev_hooks/freeze_phase_state.py --freeze
  python3 scripts/dev_hooks/freeze_phase_state.py --unfreeze-to-init
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))

FROZEN_STATE = {
    "phase_current": "_frozen",
    "phase_simple_goal": "(凍結中: 天翔十字フロー本体の改修中、フロー外で作業)",
    "phase_total": 0,
    "phase_remaining": 0,
    "latest_plan_path": "",
}

UNFROZEN_TO_INIT_STATE = {
    "phase_current": "_frozen",
    "phase_simple_goal": "(凍結中: 次回 /init-plan で初期化)",
    "phase_total": 0,
    "phase_remaining": 0,
    "latest_plan_path": "",
}


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


def _atomic_write(state_path: Path, state: dict) -> None:
    fd, tmp_path = tempfile.mkstemp(
        prefix=".phase_state.", suffix=".json", dir=str(state_path.parent)
    )
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp_path, state_path)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="phase_state.json 凍結 / 復帰 helper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--freeze",
        action="store_true",
        help="フロー外作業のために凍結 (phase_current=_frozen)",
    )
    group.add_argument(
        "--unfreeze-to-init",
        action="store_true",
        help="凍結を解いて空白化、次の /init-plan で再入力可能にする",
    )
    args = parser.parse_args(argv)

    try:
        state_path = _find_phase_state()
    except Exception as exc:
        print(f"freeze_phase_state: 読込失敗: {exc}", file=sys.stderr)
        return 1

    template = FROZEN_STATE if args.freeze else UNFROZEN_TO_INIT_STATE
    new_state = dict(template)
    new_state["updated_at"] = datetime.now(JST).isoformat(timespec="seconds")

    try:
        _atomic_write(state_path, new_state)
    except Exception as exc:
        print(f"freeze_phase_state: 書込失敗: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(new_state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
