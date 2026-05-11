"""_extract_preview の単体テスト。

メッセージ本文から会話部分のみを抽出して pixel UI のバブル / 壁面パネル用 preview にする。"""
from src.mcp_server import _extract_preview


def test_strips_bracket_header():
    assert _extract_preview("【完了報告】テストです。") == "テストです。"


def test_strips_subtask_paren():
    assert _extract_preview("ユウコさん、納品しました (subtask: abc-123-def)。") == \
        "ユウコさん、納品しました。"


def test_strips_subtask_id_paren():
    assert _extract_preview("報告です (subtask_id: 01c0f275-4c64-4bb4)") == "報告です"


def test_cuts_at_horizontal_rule():
    text = "ユウコさん、納品しました。\n---\n# 詳細\n## 納品ファイル\n- foo.html"
    assert _extract_preview(text) == "ユウコさん、納品しました。"


def test_cuts_at_markdown_heading():
    text = "報告です。本句は『新緑や』です。\n# 詳細\n納品ファイル一覧"
    assert _extract_preview(text) == "報告です。本句は『新緑や』です。"


def test_passes_through_natural_text():
    s = "ユウコさん、5月病句、納めました。"
    assert _extract_preview(s) == s


def test_combined_header_and_separator():
    text = "【完了報告】算数テスト (subtask: x-1)\n\n本日納めました。\n---\n# 詳細"
    # 先頭の角括弧を除く → 残りの自然言語は「算数テスト\n\n本日納めました。」
    # subtask は paren が無いので残るが、形式は除去対象
    out = _extract_preview(text)
    assert "【" not in out
    assert "subtask:" not in out
    assert "本日納めました" in out
    assert "# 詳細" not in out


def test_collapses_whitespace():
    assert _extract_preview("ユウコさん、\n\n  納品   しました。") == "ユウコさん、 納品 しました。"


def test_empty_returns_empty():
    assert _extract_preview("") == ""
    assert _extract_preview(None) == ""


def test_limit_applied():
    s = "あ" * 500
    out = _extract_preview(s, limit=200)
    assert len(out) == 200


def test_limit_default_200():
    s = "い" * 250
    out = _extract_preview(s)
    assert len(out) == 200
