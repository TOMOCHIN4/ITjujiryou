"""inbox_watcher の curator_request 用 backstage プロンプト整形 unit test。

サザン二重構造 (SPEC.md 後日更新予定) の裏側経路:
  watcher が `to="souther" and message_type="curator_request"` のメッセージを送る時、
  prompt 先頭に `[BACKSTAGE:curator]` sentinel を付加して送信する。inject_souther_mode.py
  はこれを検出して Omage Gate を skip する。

ここでは format ロジックの純関数だけを検証 (asyncio / tmux / DB は触らない)。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WATCHER_PATH = REPO_ROOT / "scripts" / "inbox_watcher.py"


@pytest.fixture(scope="module")
def watcher_module():
    spec = importlib.util.spec_from_file_location("inbox_watcher", WATCHER_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sample_msg() -> dict:
    return {
        "id": "abcdef12-3456",
        "from_agent": "yuko",
        "to_agent": "souther",
        "message_type": "curator_request",
        "task_id": "case-xyz",
        "content": (
            "memory_proposal 統合依頼。operation=integrate_proposal, "
            "source: data/memory/writer/_proposals/case-xyz.md"
        ),
    }


def test_format_backstage_curator_prompt_has_sentinel(watcher_module):
    out = watcher_module.format_backstage_curator_prompt(_sample_msg())
    # 先頭が sentinel
    assert out.startswith(watcher_module.BACKSTAGE_CURATOR_TAG), (
        f"prompt の先頭が sentinel ({watcher_module.BACKSTAGE_CURATOR_TAG}) ではない: {out[:80]!r}"
    )
    assert watcher_module.BACKSTAGE_CURATOR_TAG == "[BACKSTAGE:curator]"


def test_format_backstage_curator_prompt_includes_content(watcher_module):
    msg = _sample_msg()
    out = watcher_module.format_backstage_curator_prompt(msg)
    assert msg["content"] in out
    assert msg["from_agent"] in out
    assert msg["message_type"] in out
    assert msg["task_id"] in out
    # 末尾の指示文が裏側向け
    assert "memory-curator" in out
    assert "curator_response" in out


def test_format_prompt_does_not_have_sentinel(watcher_module):
    """通常 format_prompt の出力に sentinel が紛れ込まないこと (回帰防止)。"""
    msg = _sample_msg()
    msg["message_type"] = "approval_request"
    out = watcher_module.format_prompt(msg)
    assert watcher_module.BACKSTAGE_CURATOR_TAG not in out, (
        "通常 format_prompt に sentinel が混入している"
    )
    assert "[BACKSTAGE" not in out
