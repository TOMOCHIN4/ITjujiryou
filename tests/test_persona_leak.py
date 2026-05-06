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


# ---- handle_client_message の retry / mask フロー ----

import pytest


@pytest.fixture
def isolated_store(tmp_path_factory, monkeypatch):
    """テスト用の隔離 DB を用意し、シングルトンを破棄。"""
    db_path = tmp_path_factory.mktemp("persona") / "test.db"
    monkeypatch.setenv("ITJUJIRYOU_DB_PATH", str(db_path))
    import src.memory.store as store_mod
    store_mod._store_singleton = None  # type: ignore[attr-defined]
    import asyncio
    asyncio.run(store_mod.get_store().init())
    yield store_mod
    store_mod._store_singleton = None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_clean_response_no_retry(isolated_store, monkeypatch):
    """ペルソナ漏れ無しなら retry されないこと。"""
    calls = []

    async def fake_run_yuko(text, task_id=None):
        calls.append(text)
        return "お客様\n\nお世話になっております。"

    monkeypatch.setattr("src.reception.run_yuko", fake_run_yuko)
    from src.reception import handle_client_message
    out = await handle_client_message("テスト発注")
    assert out.startswith("お客様")
    assert len(calls) == 1  # retry されていない


@pytest.mark.asyncio
async def test_leak_then_clean_on_retry(isolated_store, monkeypatch):
    """初回漏れ→retry でクリーンになれば、その本文がそのまま返ること。"""
    n = {"i": 0}

    async def fake_run_yuko(text, task_id=None):
        n["i"] += 1
        if n["i"] == 1:
            return "お客様、ふん、下郎よ。承りました。"  # 漏れあり
        return "お客様、承りました。"  # クリーン

    monkeypatch.setattr("src.reception.run_yuko", fake_run_yuko)
    from src.reception import handle_client_message
    out = await handle_client_message("テスト発注")
    assert "下郎" not in out and "ふん、" not in out
    assert out == "お客様、承りました。"
    assert n["i"] == 2  # retry が起きた


@pytest.mark.asyncio
async def test_double_leak_triggers_mask(isolated_store, monkeypatch):
    """retry 後も漏れたら強制マスク (■) されること。"""
    n = {"i": 0}

    async def fake_run_yuko(text, task_id=None):
        n["i"] += 1
        return "お客様、ふん、下郎よ。承りました。"  # 何度呼んでも漏れる

    monkeypatch.setattr("src.reception.run_yuko", fake_run_yuko)
    from src.reception import handle_client_message
    out = await handle_client_message("テスト発注")
    assert "下郎" not in out and "ふん、" not in out
    assert "■" in out  # マスク済み
    assert n["i"] == 2  # 1回 retry までで止まる
