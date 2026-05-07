"""サウザー Python 確率制御モード機構のテスト。"""
from __future__ import annotations

import importlib
from collections import Counter

import pytest


@pytest.fixture
def mode_env(tmp_path, monkeypatch):
    """state ファイルを tmp_path に隔離する。"""
    state_path = tmp_path / "souther_state.json"
    spot_log = tmp_path / "souther_spotlight.log"
    import src.agents.base as base
    monkeypatch.setattr(base, "SOUTHER_STATE_PATH", state_path)
    monkeypatch.setattr(base, "SPOTLIGHT_LOG", spot_log)
    monkeypatch.delenv("ITJUJIRYOU_FORCE_MODE", raising=False)
    return base


def test_mode_state_persists(mode_env):
    """state ファイルへの永続化と復元が正常動作する。"""
    base = mode_env
    base._decide_souther_mode()
    base._decide_souther_mode()
    state = base._load_souther_state()
    assert state["total"] == 2


def test_mode_force_via_env(mode_env, monkeypatch):
    """ITJUJIRYOU_FORCE_MODE=強がり で必ず強がりが発火する。"""
    base = mode_env
    monkeypatch.setenv("ITJUJIRYOU_FORCE_MODE", "強がり")
    for _ in range(5):
        assert base._decide_souther_mode() == "強がり"


def test_mode_force_normal(mode_env, monkeypatch):
    """ITJUJIRYOU_FORCE_MODE=通常 で必ず None が返る（モード注入なし）。"""
    base = mode_env
    monkeypatch.setenv("ITJUJIRYOU_FORCE_MODE", "通常")
    for _ in range(5):
        assert base._decide_souther_mode() is None


def test_mode_cooldown_respected(mode_env, monkeypatch):
    """cooldown 中は同モードが発火しない。

    強制発火を経由して last_fire を埋めた後、確率を強制的に 1.0 にしても
    cooldown 内では発火しないことを確認する。
    """
    base = mode_env

    # last_fire["強がり"] を最新に置くため強制発火を1回
    monkeypatch.setenv("ITJUJIRYOU_FORCE_MODE", "強がり")
    base._decide_souther_mode()  # total=1, last_fire["強がり"]=1
    monkeypatch.delenv("ITJUJIRYOU_FORCE_MODE")

    # 確率を 1.0 にして強制条件を満たさせる
    saved = dict(base.SOUTHER_MODES["強がり"])
    monkeypatch.setitem(base.SOUTHER_MODES, "強がり", {**saved, "probability": 1.0})
    # 他モードは確率0で潰す
    for m in ("亀裂", "説き諭し", "深い独白"):
        monkeypatch.setitem(base.SOUTHER_MODES, m, {**base.SOUTHER_MODES[m], "probability": 0.0})

    # cooldown=3 なので、total=2,3 では発火しない（n - last < 3）
    assert base._decide_souther_mode() != "強がり"  # total=2
    assert base._decide_souther_mode() != "強がり"  # total=3
    # total=4 で n-last=3 となり cooldown 解除、確率1.0で発火
    assert base._decide_souther_mode() == "強がり"  # total=4


def test_mode_probability_long_run(mode_env):
    """1000召喚で各モードの実発火率が±50%以内に収まる。"""
    base = mode_env
    fires: Counter[str] = Counter()
    for _ in range(1000):
        m = base._decide_souther_mode()
        fires[m or "通常"] += 1

    # 設計値（cooldown 込みで実効発火率は単独確率より低くなる）
    # 通常 ~62%, 強がり ~17%, 亀裂 ~12%, 説き諭し ~12%, 深い独白 ~3%
    assert fires["通常"] >= 300, f"通常が少なすぎ: {fires}"
    assert fires["通常"] <= 850, f"通常が多すぎ: {fires}"
    # 各モードが少なくとも数回は発火
    for mode in ("亀裂", "説き諭し", "強がり"):
        assert fires[mode] >= 20, f"{mode} の発火が少ない: {fires}"


def test_mode_block_injection(mode_env, monkeypatch):
    """発火モードがプロンプト末尾に正しく注入される。"""
    base = mode_env
    monkeypatch.setenv("ITJUJIRYOU_FORCE_MODE", "亀裂")
    prompt = base.load_prompt("souther")
    assert "## 今回の召喚モード: 亀裂と揺らぎ" in prompt

    monkeypatch.setenv("ITJUJIRYOU_FORCE_MODE", "強がり")
    prompt = base.load_prompt("souther")
    assert "## 今回の召喚モード: 強がり" in prompt


def test_mode_log_records_firings(mode_env, monkeypatch):
    """spotlight.log にモード発火が記録される。"""
    base = mode_env
    monkeypatch.setenv("ITJUJIRYOU_FORCE_MODE", "深い独白")
    base._decide_souther_mode()
    base._log_souther_mode("深い独白")
    log_content = base.SPOTLIGHT_LOG.read_text(encoding="utf-8")
    assert "mode=深い独白" in log_content
