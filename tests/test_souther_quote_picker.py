"""Omage Gate (inject_souther_mode.py) の parser / cooldown / output unit test。

設計の根拠は SPEC.md §7.1。サザンの返答制御 = quotes.md パース + 3 抽選 + Claude
への omage 指示テンプレ生成、までを純粋関数として検証する。tmux / claude プロセスは
立ち上げない。
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "hooks" / "inject_souther_mode.py"
QUOTES_PATH = REPO_ROOT / "workspaces" / "souther" / "_modules" / "quotes.md"


@pytest.fixture(scope="module")
def hook_module():
    """inject_souther_mode.py を module として import する。ファイル名にハイフンが
    無いのでそのまま import 可能だが、scripts/ が sys.path に無いため spec_from_file_location 経由"""
    spec = importlib.util.spec_from_file_location("inject_souther_mode", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_quotes_md_exists():
    assert QUOTES_PATH.exists(), f"quotes source missing: {QUOTES_PATH}"


def test_parse_quotes_returns_27_entries(hook_module):
    quotes = hook_module._parse_quotes(QUOTES_PATH.read_text(encoding="utf-8"))
    assert len(quotes) == 27, f"expected 27 entries, got {len(quotes)}"


def test_parse_quotes_required_meta(hook_module):
    quotes = hook_module._parse_quotes(QUOTES_PATH.read_text(encoding="utf-8"))
    required = {"原作文脈", "感情の核", "事務所での出番", "変奏ヒント"}
    for q in quotes:
        assert q["no"] >= 1
        assert isinstance(q["theme"], str) and q["theme"]
        assert isinstance(q["quote"], str) and q["quote"]
        missing = required - q["meta"].keys()
        assert not missing, f"#{q['no']} missing meta: {missing}"


def test_pick_three_respects_cooldown(hook_module):
    quotes = [{"no": i, "theme": f"t{i}", "quote": "q", "meta": {}} for i in range(1, 28)]
    # 直近 5 picks で 15 quote を除外 → 残り 12 から 3 つ
    recent = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [10, 11, 12],
        [13, 14, 15],
    ]
    picks = hook_module._pick_three(quotes, recent)
    assert len(picks) == 3
    picked_nos = {q["no"] for q in picks}
    assert picked_nos.isdisjoint({n for ps in recent for n in ps})


def test_pick_three_fallback_when_pool_too_small(hook_module):
    quotes = [{"no": i, "theme": "t", "quote": "q", "meta": {}} for i in range(1, 6)]
    # 5 quote のうち 3 件除外 → pool 2 件で PICK_COUNT(3) 未満 → 全 quote から選び直す
    recent = [[1, 2, 3]]
    picks = hook_module._pick_three(quotes, recent)
    assert len(picks) == 3


def test_build_omage_context_contains_three_candidates(hook_module):
    picks = [
        {"no": 13, "theme": "拳の哲学・制圧前進", "quote": "わが拳にあるのはただ制圧前進のみ！！",
         "meta": {"変奏ヒント": "前進あるのみ", "感情の核": "迷いなし",
                  "事務所での出番": "部下への喝", "原作文脈": "..."}},
        {"no": 24, "theme": "食通の癇癪・評価", "quote": "今日のは口に合わぬ",
         "meta": {"変奏ヒント": "投げ捨てる", "感情の核": "端的な拒絶",
                  "事務所での出番": "差し戻し", "原作文脈": "..."}},
        {"no": 22, "theme": "余裕の演技・強がり", "quote": "ひと～つ、ふた～つ、みぃ～つ!!",
         "meta": {"変奏ヒント": "数を数える", "感情の核": "強がり",
                  "事務所での出番": "脅し返し", "原作文脈": "..."}},
    ]
    ctx = hook_module._build_omage_context("テスト報告本文", picks)
    assert "## 報告受信" in ctx
    assert "テスト報告本文" in ctx
    assert "## 今回の召喚で念頭に置く三選" in ctx
    assert "### 候補 1:" in ctx
    assert "### 候補 2:" in ctx
    assert "### 候補 3:" in ctx
    assert "#13.【拳の哲学・制圧前進】" in ctx
    assert "#24.【食通の癇癪・評価】" in ctx
    assert "#22.【余裕の演技・強がり】" in ctx
    assert "## 返答ルール (Omage Gate 厳守)" in ctx
    assert 'send_message' in ctx
    assert 'to="yuko"' in ctx


def test_hook_end_to_end_outputs_valid_json(tmp_path, monkeypatch):
    """hook を subprocess で実行して、JSON 出力が Claude Code 仕様に合うか検証。

    実 state ファイルを書き換えないよう、HOME を tmp に逃がす — 直接的でなく
    `data/logs/souther_state.json` をテストではなく実体パスに書くため、ここでは
    state 書き換え副作用を許容しつつ JSON 形状だけ検証する。
    """
    event = {"hook_event_name": "UserPromptSubmit", "prompt": "ユウコより上申: ハオウの初稿 200 字、確認願う"}
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, f"hook exited non-zero: stderr={result.stderr}"
    parsed = json.loads(result.stdout)
    assert "hookSpecificOutput" in parsed
    out = parsed["hookSpecificOutput"]
    assert out["hookEventName"] == "UserPromptSubmit"
    assert "additionalContext" in out
    ctx = out["additionalContext"]
    assert "RESPONSE CONSTRAINTS" in ctx
    assert "## 報告受信" in ctx
    assert "ハオウの初稿" in ctx
    assert "## 今回の召喚で念頭に置く三選" in ctx
