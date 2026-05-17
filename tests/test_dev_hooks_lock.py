"""dev_hooks 物理ガードのリグレッションテスト。

天翔十字フローの不変キー (phase_simple_goal / phase_total) が
advance_phase_state.py 経由で書き換えられないこと、
進行中フローを init_phase_state.py で潰せないことを保証する。

テスト用 phase_state.json は ITJ_PHASE_STATE_PATH env var で切替える。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INIT_HELPER = REPO_ROOT / "scripts" / "dev_hooks" / "init_phase_state.py"
ADVANCE_HELPER = REPO_ROOT / "scripts" / "dev_hooks" / "advance_phase_state.py"

FROZEN_STATE = {
    "phase_current": "_frozen",
    "phase_simple_goal": "(凍結中)",
    "phase_total": 0,
    "phase_remaining": 0,
    "latest_plan_path": "",
    "updated_at": "2026-05-17T00:00:00+09:00",
}

RUNNING_STATE = {
    "phase_current": "A",
    "phase_simple_goal": "テスト用シンプルゴール",
    "phase_total": 3,
    "phase_remaining": 2,
    "latest_plan_path": ".claude/plans/phase_A.md",
    "updated_at": "2026-05-17T00:00:00+09:00",
}


def _write_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_helper(helper: Path, state_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["ITJ_PHASE_STATE_PATH"] = str(state_path)
    return subprocess.run(
        [sys.executable, str(helper), *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_advance_normal_keeps_immutable(tmp_path: Path) -> None:
    state_path = tmp_path / "phase_state.json"
    _write_state(state_path, RUNNING_STATE)

    r = _run_helper(
        ADVANCE_HELPER,
        state_path,
        "phase_current=B",
        "phase_remaining=1",
        "latest_plan_path=.claude/plans/phase_B.md",
    )
    assert r.returncode == 0, r.stderr

    after = json.loads(state_path.read_text(encoding="utf-8"))
    assert after["phase_current"] == "B"
    assert after["phase_remaining"] == 1
    assert after["latest_plan_path"] == ".claude/plans/phase_B.md"
    assert after["phase_simple_goal"] == RUNNING_STATE["phase_simple_goal"]
    assert after["phase_total"] == RUNNING_STATE["phase_total"]


def test_advance_rejects_simple_goal_overwrite(tmp_path: Path) -> None:
    state_path = tmp_path / "phase_state.json"
    _write_state(state_path, RUNNING_STATE)
    before_text = state_path.read_text(encoding="utf-8")

    r = _run_helper(ADVANCE_HELPER, state_path, "phase_simple_goal=hack")
    assert r.returncode == 1
    assert "phase_simple_goal" in r.stderr

    assert state_path.read_text(encoding="utf-8") == before_text


def test_advance_rejects_total_overwrite(tmp_path: Path) -> None:
    state_path = tmp_path / "phase_state.json"
    _write_state(state_path, RUNNING_STATE)
    before_text = state_path.read_text(encoding="utf-8")

    r = _run_helper(ADVANCE_HELPER, state_path, "phase_total=5")
    assert r.returncode == 1
    assert "phase_total" in r.stderr

    assert state_path.read_text(encoding="utf-8") == before_text


def test_advance_rejects_when_frozen(tmp_path: Path) -> None:
    state_path = tmp_path / "phase_state.json"
    _write_state(state_path, FROZEN_STATE)
    before_text = state_path.read_text(encoding="utf-8")

    r = _run_helper(
        ADVANCE_HELPER,
        state_path,
        "phase_current=B",
        "phase_remaining=1",
        "latest_plan_path=.claude/plans/phase_B.md",
    )
    assert r.returncode == 1
    assert "進行中フロー" in r.stderr

    assert state_path.read_text(encoding="utf-8") == before_text


def test_init_rejects_when_running(tmp_path: Path) -> None:
    state_path = tmp_path / "phase_state.json"
    _write_state(state_path, RUNNING_STATE)
    before_text = state_path.read_text(encoding="utf-8")

    r = _run_helper(
        INIT_HELPER,
        state_path,
        "phase_current=A",
        "phase_simple_goal=hack",
        "phase_total=3",
        "phase_remaining=2",
        "latest_plan_path=.claude/plans/phase_A.md",
    )
    assert r.returncode == 1
    assert "_frozen" in r.stderr

    assert state_path.read_text(encoding="utf-8") == before_text
