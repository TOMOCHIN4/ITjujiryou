"""ペルソナ境界: クライアント向け応答に内部用語が含まれないこと。

マルチプロセス構成では、ライブ E2E は tmux + Claude Code の OAuth セッションが必要。
ここでは以下を検証する:
1. FORBIDDEN_TERMS リストの完全性
2. find_forbidden_terms フィルタの挙動
3. PreToolUse hook (`scripts/hooks/check_persona_leak.py`) が漏れを deny すること
4. PreToolUse hook (`scripts/hooks/check_souther_recipient.py`) が社長の to=client を deny すること
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.persona import FORBIDDEN_TERMS, find_forbidden_terms

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def test_forbidden_terms_cover_core_persona():
    must_include = [
        "聖帝", "サウザー", "南斗", "下郎", "退かぬ", "媚びぬ", "省みぬ",
        "ケンシロウ", "北斗", "鳳凰拳", "オウガイ",
        # v3.1 世界観刷新で追加した前世名・社内符丁
        "ラオウ", "トキ", "拳王", "愛帝",
        "死兆星", "アタタタタタッ", "天に帰る", "制圧前進",
        "激流を制するのは静水",
    ]
    for term in must_include:
        assert term in FORBIDDEN_TERMS, f"{term} が FORBIDDEN_TERMS に含まれていない"


def test_forbidden_terms_detect_new_persona_leaks():
    """新世界観の社内符丁・前世名がクライアント宛文書から弾かれること。"""
    cases = [
        ("お前の頭上に死兆星が見えるぞ", "死兆星"),
        ("アタタタタタッ！対応します", "アタタタタタッ"),
        ("修正は天に帰るで受領しました", "天に帰る"),
        ("我が社にあるのは制圧前進のみ", "制圧前進"),
        ("ラオウから引き継いだ姿勢で", "ラオウ"),
        ("トキの慈愛をデザインに", "トキ"),
        ("拳王の名にかけて", "拳王"),
        ("激流を制するのは静水です", "激流を制するのは静水"),
    ]
    for text, expected in cases:
        leaks = find_forbidden_terms(text)
        assert expected in leaks, f"{expected!r} が検出されなかった: text={text!r} → {leaks}"


def test_find_forbidden_terms_detects_leak():
    leaks = find_forbidden_terms("ふん、下郎よ。聖帝の流儀に従え。")
    assert "下郎" in leaks
    assert "聖帝" in leaks
    assert "ふん、" in leaks


def test_find_forbidden_terms_clean_passes():
    clean = "お客様、ご依頼の件、確認いたしました。よろしくお願いいたします。"
    assert find_forbidden_terms(clean) == []


# ---- hook の挙動 ----


def _run_hook(script: str, event: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, str(REPO_ROOT / "scripts" / "hooks" / script)],
        input=json.dumps(event),
        text=True,
        capture_output=True,
        check=False,
    )


def test_persona_leak_hook_denies_deliver_with_forbidden():
    ev = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__itjujiryou__deliver",
        "tool_input": {"delivery_message": "お客様、ふん、聖帝の流儀により納品します"},
    }
    r = _run_hook("check_persona_leak.py", ev)
    assert r.returncode == 2, f"deny されなかった: stderr={r.stderr}"
    assert "ふん、" in r.stderr or "聖帝" in r.stderr


def test_persona_leak_hook_passes_clean_deliver():
    ev = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__itjujiryou__deliver",
        "tool_input": {"delivery_message": "お客様、ご依頼の件、納品いたします。"},
    }
    r = _run_hook("check_persona_leak.py", ev)
    assert r.returncode == 0, f"clean でも deny された: stderr={r.stderr}"


def test_persona_leak_hook_skips_internal_send_message():
    """社内通信 (to != client) はペルソナ用語を含んでも素通しすること。"""
    ev = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__itjujiryou__send_message",
        "tool_input": {"to": "yuko", "content": "ふん、下郎の頼みは却下せよ"},
    }
    r = _run_hook("check_persona_leak.py", ev)
    assert r.returncode == 0, "社内通信が誤って deny された"


def test_souther_recipient_hook_denies_to_client():
    ev = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__itjujiryou__send_message",
        "tool_input": {"to": "client", "content": "勝手に送る"},
    }
    r = _run_hook("check_souther_recipient.py", ev)
    assert r.returncode == 2, f"deny されなかった: stderr={r.stderr}"


def test_souther_recipient_hook_allows_to_yuko():
    ev = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__itjujiryou__send_message",
        "tool_input": {"to": "yuko", "content": "ふん、許す"},
    }
    r = _run_hook("check_souther_recipient.py", ev)
    assert r.returncode == 0
