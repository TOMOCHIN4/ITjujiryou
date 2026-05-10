"""evaluate_deliverable handler のルーブリック検証テスト。

10 軸 0-5 の scores を渡したとき、bn 推奨 decision との乖離が周回別に
警告/情報メッセージで返ることを検証。"""
import json

import pytest

from src.memory import store as store_mod
from src.memory.store import Store
from src.mcp_server import _handle_evaluate_deliverable, _recommend_decision, _validate_scores


def _scores_json(values):
    """10 個の整数 → 形式に従う scores JSON 文字列。"""
    assert len(values) == 10
    axes = [
        {"name": f"軸{i}", "score": v, "rationale": "テスト用根拠"}
        for i, v in enumerate(values)
    ]
    return json.dumps({"axes": axes})


@pytest.fixture
async def fresh_store(tmp_path, monkeypatch):
    monkeypatch.setenv("ITJUJIRYOU_LOG_PATH", str(tmp_path / "timeline.log"))
    s = Store(db_path=tmp_path / "t.db")
    await s.init()
    monkeypatch.setattr(store_mod, "_store_singleton", s)
    return s


@pytest.fixture
async def task_and_subtask(fresh_store):
    tid = await fresh_store.create_task("t", "d", "r")
    sid = await fresh_store.create_subtask(tid, "writer", "exec")
    return tid, sid


def _text_of(result) -> str:
    return result[0].text


# ---- _validate_scores 単体 ----

def test_validate_scores_invalid_json():
    axes, err = _validate_scores("not json")
    assert axes is None and "parse 失敗" in err


def test_validate_scores_missing_axes_key():
    axes, err = _validate_scores('{"foo": 1}')
    assert axes is None and "axes" in err


def test_validate_scores_wrong_count():
    bad = json.dumps({"axes": [{"name": "x", "score": 5, "rationale": "y"}] * 9})
    axes, err = _validate_scores(bad)
    assert axes is None and "10" in err


def test_validate_scores_missing_field():
    bad = json.dumps({"axes": [{"name": "x", "score": 5}] * 10})
    axes, err = _validate_scores(bad)
    assert axes is None and "rationale" in err


def test_validate_scores_out_of_range():
    bad = json.dumps({
        "axes": [{"name": "x", "score": 6, "rationale": "y"}] + [{"name": "x", "score": 5, "rationale": "y"}] * 9
    })
    axes, err = _validate_scores(bad)
    assert axes is None and "範囲" in err


def test_validate_scores_score_must_be_int():
    bad = json.dumps({
        "axes": [{"name": "x", "score": 4.5, "rationale": "y"}] * 10
    })
    axes, err = _validate_scores(bad)
    assert axes is None and "整数" in err


def test_validate_scores_ok():
    good = _scores_json([5] * 10)
    axes, err = _validate_scores(good)
    assert err is None and len(axes) == 10


# ---- _recommend_decision 単体 ----

def test_recommend_zero_axis_escalates():
    axes = [{"score": 0}] + [{"score": 5}] * 9
    assert _recommend_decision(axes) == "escalate_to_president"


def test_recommend_minimum_two_revises():
    axes = [{"score": 2}] + [{"score": 5}] * 9
    assert _recommend_decision(axes) == "revise"


def test_recommend_full_high_approves():
    axes = [{"score": 4}] * 5 + [{"score": 5}] * 5  # total=45, min=4
    assert _recommend_decision(axes) == "approve"


def test_recommend_low_total_escalates():
    axes = [{"score": 3}] * 10  # total=30, min=3
    assert _recommend_decision(axes) == "escalate_to_president"


def test_recommend_borderline_revises():
    # min=3, total=37 → revise (33 < total < 44)
    axes = [{"score": 3}] * 5 + [{"score": 4}] * 5  # total=35
    assert _recommend_decision(axes) == "revise"


# ---- handler ----

async def test_handler_rejects_invalid_decision(task_and_subtask):
    tid, sid = task_and_subtask
    res = await _handle_evaluate_deliverable({
        "task_id": tid, "subtask_id": sid,
        "evaluation": "ok", "decision": "BOGUS",
    })
    assert "ERROR" in _text_of(res)


async def test_handler_warns_when_scores_omitted(task_and_subtask):
    tid, sid = task_and_subtask
    res = await _handle_evaluate_deliverable({
        "task_id": tid, "subtask_id": sid,
        "evaluation": "ok", "decision": "approve",
    })
    text = _text_of(res)
    assert "scores 未指定" in text
    # 互換: 受理されて記録されること
    assert "評価記録" in text


async def test_handler_rejects_invalid_scores_json(task_and_subtask):
    tid, sid = task_and_subtask
    res = await _handle_evaluate_deliverable({
        "task_id": tid, "subtask_id": sid,
        "evaluation": "ok", "decision": "approve",
        "scores": "{ not valid",
    })
    assert _text_of(res).startswith("ERROR")


async def test_handler_full_high_score_approve_no_warning(task_and_subtask):
    tid, sid = task_and_subtask
    res = await _handle_evaluate_deliverable({
        "task_id": tid, "subtask_id": sid,
        "evaluation": "ok", "decision": "approve",
        "scores": _scores_json([5] * 10),
    })
    text = _text_of(res)
    assert "推奨 decision=approve" in text
    assert "⚠" not in text  # 一致しているので警告なし


async def test_handler_zero_score_with_approve_warns(task_and_subtask):
    tid, sid = task_and_subtask
    scores = _scores_json([0] + [5] * 9)
    res = await _handle_evaluate_deliverable({
        "task_id": tid, "subtask_id": sid,
        "evaluation": "押し通す", "decision": "approve",
        "round": 0,
        "scores": scores,
    })
    text = _text_of(res)
    assert "⚠" in text
    assert "escalate_to_president" in text


async def test_handler_final_round_dissonance_uses_info_tone(task_and_subtask):
    """3 周目 (round=2 = MAX_REVISION_ROUNDS) では ℹ で受理する。"""
    tid, sid = task_and_subtask
    scores = _scores_json([3] * 10)  # 推奨 escalate
    res = await _handle_evaluate_deliverable({
        "task_id": tid, "subtask_id": sid,
        "evaluation": "最終ラウンドの裁量", "decision": "approve",
        "round": 2,
        "scores": scores,
    })
    text = _text_of(res)
    assert "ℹ" in text
    assert "最終ラウンド" in text
    assert "⚠" not in text


async def test_handler_persists_scores_in_db(fresh_store, task_and_subtask):
    tid, sid = task_and_subtask
    scores = _scores_json([4] * 10)
    await _handle_evaluate_deliverable({
        "task_id": tid, "subtask_id": sid,
        "evaluation": "ok", "decision": "revise",
        "round": 0,
        "scores": scores,
    })
    revs = await fresh_store.list_revisions(tid)
    assert len(revs) == 1
    saved = json.loads(revs[0]["scores"])
    assert len(saved["axes"]) == 10
    assert saved["axes"][0]["score"] == 4
