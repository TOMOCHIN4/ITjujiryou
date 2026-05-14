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


def test_extract_message_type_strips_request_suffix(hook_module):
    """`type: xxx_request` 行から `_request` を除いた値を返す。"""
    prompt = (
        "新着メッセージ (msg_id=abc):\n"
        "  from: yuko\n"
        "  type: memory_approval_request\n"
        "  task_id: case-1\n"
        "---\n"
        "本文\n"
        "---\n"
    )
    assert hook_module._extract_message_type(prompt) == "memory_approval"

    prompt2 = (
        "新着メッセージ (msg_id=xyz):\n"
        "  from: yuko\n"
        "  type: approval_request\n"
        "  task_id: case-2\n"
        "---\n"
        "本文\n"
        "---\n"
    )
    assert hook_module._extract_message_type(prompt2) == "approval"


def test_extract_message_type_fallback_when_no_type_line(hook_module):
    """type 行が無い prompt は `approval` フォールバック。"""
    assert hook_module._extract_message_type("ユウコより上申: 評価頼む") == "approval"
    assert hook_module._extract_message_type("") == "approval"
    assert hook_module._extract_message_type("from: yuko\n本文だけ\n") == "approval"


def test_extract_message_type_handles_carriage_return(hook_module):
    """watcher が tmux 経由で投入する prompt は `\\r` 改行で届く (verify-003 v5 で発覚)。
    `\\r` 単独・`\\r\\n` 両方を normalize して type 行を抽出できること。"""
    cr_prompt = (
        "新着メッセージ (msg_id=abc):\r"
        "  from: yuko\r"
        "  type: memory_approval_request\r"
        "  task_id: case-1\r"
        "---\r"
        "本文\r"
        "---\r"
    )
    assert hook_module._extract_message_type(cr_prompt) == "memory_approval"

    crlf_prompt = (
        "新着メッセージ (msg_id=xyz):\r\n"
        "  from: yuko\r\n"
        "  type: approval_request\r\n"
        "  task_id: case-2\r\n"
        "---\r\n"
        "本文\r\n"
        "---\r\n"
    )
    assert hook_module._extract_message_type(crlf_prompt) == "approval"


def test_build_omage_context_uses_reply_type_in_send_message(hook_module):
    """reply_type 引数が omage 指示テンプレの send_message message_type に埋め込まれる。"""
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
    ctx_memory = hook_module._build_omage_context(
        "テスト報告本文", picks, reply_type="memory_approval"
    )
    assert 'message_type="memory_approval"' in ctx_memory
    assert 'message_type="approval"' not in ctx_memory  # 上書きされる

    # デフォルト引数の挙動: reply_type 省略時は "approval"
    ctx_default = hook_module._build_omage_context("テスト報告本文", picks)
    assert 'message_type="approval"' in ctx_default


def test_hook_e2e_memory_approval_type(tmp_path, monkeypatch):
    """subprocess で hook を起動、prompt の type: memory_approval_request を見て
    出力 additionalContext に `message_type="memory_approval"` が含まれることを確認。"""
    event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": (
            "新着メッセージ (msg_id=abc):\n"
            "  from: yuko\n"
            "  type: memory_approval_request\n"
            "  task_id: case-1\n"
            "---\n"
            "サザン社長、儀礼承認のお伺いです。\n"
            "---\n"
        ),
    }
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, f"hook exited non-zero: stderr={result.stderr}"
    ctx = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert 'message_type="memory_approval"' in ctx, (
        "Omage 指示が memory_approval_request 受領時に memory_approval を返すよう"
        "指示していない (workaround 残存)"
    )


def test_is_backstage_helper(hook_module):
    """裏側 sentinel 判定の単純ヘルパ。"""
    assert hook_module._is_backstage("[BACKSTAGE:curator]\nfoo") is True
    assert hook_module._is_backstage("  [BACKSTAGE:curator] body") is True
    assert hook_module._is_backstage("普通の上申") is False
    assert hook_module._is_backstage("[BACKSTAGE:other] body") is False


def test_build_silent_context_contents(hook_module):
    """裏側 silent context が必要な指示語を含むこと。"""
    ctx = hook_module._build_silent_context(
        "[BACKSTAGE:curator]\ncurator_request body for integrate_proposal"
    )
    assert "裏側" in ctx
    assert "memory-curator" in ctx
    assert "curator_response" in ctx
    assert "聖帝口調は不要" in ctx
    # Omage Gate 用の見出しは含まれない (skip の証拠)
    assert "## 報告受信" not in ctx
    assert "今回の召喚で念頭に置く三選" not in ctx
    # 本文が context に取り込まれる (sentinel は除去済)
    assert "integrate_proposal" in ctx
    assert "[BACKSTAGE:curator]" not in ctx  # sentinel 自体は除去


def test_hook_skips_omage_for_backstage_sentinel(tmp_path, monkeypatch):
    """subprocess で hook を起動し、[BACKSTAGE:curator] 先頭 prompt で
    Omage Gate が skip されて silent context のみ注入されることを確認。"""
    event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "[BACKSTAGE:curator]\nユウコより curator_request: operation=integrate_proposal",
    }
    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, f"hook exited non-zero: stderr={result.stderr}"
    parsed = json.loads(result.stdout)
    ctx = parsed["hookSpecificOutput"]["additionalContext"]
    # Omage Gate の見出しが含まれない (skip 確認)
    assert "## 報告受信" not in ctx
    assert "今回の召喚で念頭に置く三選" not in ctx
    # silent モード用の指示が含まれる
    assert "裏側" in ctx
    assert "memory-curator" in ctx
    assert "curator_response" in ctx


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
