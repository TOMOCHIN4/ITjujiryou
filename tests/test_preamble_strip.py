"""ユウコ応答の内部独白プリアンブル剥がしの単体テスト。"""
from src.reception import _strip_internal_preamble, find_forbidden_terms


def test_strip_typical_engineer_preamble():
    raw = (
        "品質は要件を満たしている。承認して納品へ進む。\n"
        "---\n\n"
        "お客様\n\n"
        "いつもお世話になっております。"
    )
    out = _strip_internal_preamble(raw)
    assert out.startswith("お客様")
    assert "承認して納品へ進む" not in out


def test_strip_discount_refusal_preamble():
    raw = (
        "値引き要望は社長のご裁断に従い、お断りします。\n"
        "本段階では dispatch / deliver は行わず再回答待ちです。\n"
        "社内ツールはクライアント宛送信不可のため、最終応答テキストとして以下:\n"
        "\n---\n\n"
        "○○様\n\n"
        "お世話になっております。"
    )
    out = _strip_internal_preamble(raw)
    assert out.startswith("○○様")


def test_keep_normal_response_with_no_separator():
    raw = "お客様\n\nお世話になっております。記事をお納めします。"
    assert _strip_internal_preamble(raw) == raw


def test_keep_response_with_decorative_dash_inside_letter():
    """本文中の装飾的 `---` は内部独白キーワードを伴わないので触らない。"""
    raw = (
        "お客様\n\n"
        "下記のとおりご納品いたします。\n"
        "---\n"
        "ここに本文。\n"
    )
    assert _strip_internal_preamble(raw) == raw


def test_hiragana_persona_terms_caught():
    text = "本件は社長の「ひかぬ」精神に従いお断りいたします。"
    assert "ひかぬ" in find_forbidden_terms(text)
