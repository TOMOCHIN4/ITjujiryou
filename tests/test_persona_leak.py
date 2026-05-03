"""ペルソナ境界: クライアント向け応答に内部用語が含まれないこと。

ライブ E2E は claude-agent-sdk と OAuth ログインが必要なため、ここでは
FORBIDDEN_TERMS リストの完全性とフィルタ関数の挙動のみを検証する。
"""
from src.reception import FORBIDDEN_TERMS, find_forbidden_terms


def test_forbidden_terms_cover_core_persona():
    must_include = [
        "聖帝", "サウザー", "南斗", "下郎", "退かぬ", "媚びぬ", "省みぬ",
        "ケンシロウ", "北斗", "鳳凰拳", "オウガイ",
    ]
    for term in must_include:
        assert term in FORBIDDEN_TERMS, f"{term} が FORBIDDEN_TERMS に含まれていない"


def test_find_forbidden_terms_detects_leak():
    leaks = find_forbidden_terms("ふん、下郎よ。聖帝の流儀に従え。")
    assert "下郎" in leaks
    assert "聖帝" in leaks
    assert "ふん、" in leaks


def test_find_forbidden_terms_clean_passes():
    clean = "お客様、ご依頼の件、確認いたしました。よろしくお願いいたします。"
    assert find_forbidden_terms(clean) == []
