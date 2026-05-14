"""会社記憶確定フロー (process_memory_approval) の検証。

サザン → ユウコ memory_approval を受領した watcher が:
  1. proposal を data/memory/company/{category}/{slug}.md に物理反映
  2. _last_write.log に JSONL 追記
  3. _proposals/_archived/{case_id}.md へ移送
  4. ユウコへ memory_finalized 通知
を行うことを検証する。

物理ファイル系のテストなので REPO_ROOT 直下を一時的に汚さないよう、
inbox_watcher の REPO_ROOT 解決を monkeypatch で書き換える。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.inbox_watcher as iw
from src.memory.store import Store, get_store
import src.memory.store as store_mod


@pytest.fixture
async def isolated_env(tmp_path, monkeypatch):
    """REPO_ROOT を tmp_path に向け、Store singleton も tmp DB に向ける。"""
    monkeypatch.setattr(iw, "REPO_ROOT", tmp_path)
    (tmp_path / "data" / "memory" / "company" / "_proposals").mkdir(parents=True)

    db_path = tmp_path / "office.db"
    monkeypatch.setattr(store_mod, "_store_singleton", None)
    monkeypatch.setenv("ITJUJIRYOU_DB_PATH", str(db_path))
    s = get_store()
    await s.init()
    return tmp_path, s


def _write_proposal(tmp_path: Path, case_id: str, body: str) -> Path:
    p = tmp_path / "data" / "memory" / "company" / "_proposals" / f"{case_id}.md"
    p.write_text(body, encoding="utf-8")
    return p


async def test_memory_approval_writes_company_file(isolated_env):
    tmp_path, store = isolated_env
    case_id = "case-001"
    proposal_body = (
        "---\n"
        "schema: proposal/v1\n"
        "case_id: case-001\n"
        "case_type: business-greeting\n"
        "target_category: quality_bar\n"
        "target_slug: concise-greeting\n"
        "contributors: [writer, yuko]\n"
        "keywords: [挨拶, 200字]\n"
        "---\n\n"
        "## 採用した方針\n"
        "200字以内の挨拶では「お世話になっております」を基調とする。\n"
    )
    proposal_path = _write_proposal(tmp_path, case_id, proposal_body)

    msg_id = await store.add_message(
        from_agent="souther",
        to_agent="yuko",
        content="ふん、認めよう",
        message_type="memory_approval",
        task_id=case_id,
    )
    msg = {
        "id": msg_id,
        "from_agent": "souther",
        "to_agent": "yuko",
        "content": "ふん、認めよう",
        "message_type": "memory_approval",
        "task_id": case_id,
    }

    result = await iw.process_memory_approval(msg)

    assert result["action"] == "finalized"
    written = tmp_path / "data" / "memory" / "company" / "quality_bar" / "concise-greeting.md"
    assert written.exists(), f"会社記憶ファイルが生成されていない: {written}"
    content = written.read_text(encoding="utf-8")
    assert "schema: company-memory/v1" in content
    assert "category: quality_bar" in content
    assert "approved_by: souther" in content
    assert "お世話になっております" in content

    assert not proposal_path.exists(), "_proposals/ から移送されていない"
    archived = tmp_path / "data" / "memory" / "company" / "_proposals" / "_archived" / f"{case_id}.md"
    assert archived.exists(), f"_archived/ に移送されていない: {archived}"


async def test_memory_approval_appends_last_write_log(isolated_env):
    tmp_path, store = isolated_env
    case_id = "case-log-001"
    _write_proposal(
        tmp_path,
        case_id,
        "---\n"
        "schema: proposal/v1\n"
        "case_id: case-log-001\n"
        "target_category: workflow_rule\n"
        "target_slug: deliver-checklist\n"
        "contributors: [yuko]\n"
        "---\n\n"
        "## 内容\n本文\n",
    )
    msg_id = await store.add_message(
        "souther", "yuko", "許す", "memory_approval", case_id
    )
    msg = {
        "id": msg_id,
        "from_agent": "souther",
        "to_agent": "yuko",
        "content": "許す",
        "message_type": "memory_approval",
        "task_id": case_id,
    }
    await iw.process_memory_approval(msg)

    log_path = tmp_path / "data" / "memory" / "company" / "_last_write.log"
    assert log_path.exists()
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["task_id"] == case_id
    assert entry["approval_msg_id"] == msg_id
    assert entry["category"] == "workflow_rule"
    assert entry["written_path"].endswith("workflow_rule/deliver-checklist.md")


async def test_memory_approval_sends_finalized_notification(isolated_env):
    tmp_path, store = isolated_env
    case_id = "case-notify-001"
    _write_proposal(
        tmp_path,
        case_id,
        "---\n"
        "schema: proposal/v1\n"
        "case_id: case-notify-001\n"
        "target_category: recurring_pattern\n"
        "target_slug: ai-intro-style\n"
        "---\n\n本文\n",
    )
    msg_id = await store.add_message(
        "souther", "yuko", "ふん、よかろう", "memory_approval", case_id
    )
    msg = {
        "id": msg_id,
        "from_agent": "souther",
        "to_agent": "yuko",
        "content": "ふん、よかろう",
        "message_type": "memory_approval",
        "task_id": case_id,
    }
    result = await iw.process_memory_approval(msg)

    finalized_id = result["finalized_msg_id"]
    msgs = await store.list_messages(case_id)
    finalized = [m for m in msgs if m["id"] == finalized_id]
    assert len(finalized) == 1
    assert finalized[0]["message_type"] == "memory_finalized"
    assert finalized[0]["to_agent"] == "yuko"
    assert "会社記憶確定" in finalized[0]["content"]


async def test_memory_approval_rejection_short_circuits(isolated_env):
    tmp_path, store = isolated_env
    case_id = "case-reject-001"
    proposal_path = _write_proposal(
        tmp_path,
        case_id,
        "---\nschema: proposal/v1\ncase_id: case-reject-001\n---\n本文\n",
    )

    msg = {
        "id": "msg-reject-1",
        "from_agent": "souther",
        "to_agent": "yuko",
        "content": "却下",
        "message_type": "memory_approval",
        "task_id": case_id,
    }
    result = await iw.process_memory_approval(msg)
    assert result["action"] == "rejected"
    # proposal はそのまま残り、_archived/ にも入っていない
    assert proposal_path.exists()


async def test_memory_approval_missing_proposal_skips(isolated_env):
    tmp_path, store = isolated_env
    case_id = "case-missing-001"
    msg = {
        "id": "msg-missing-1",
        "from_agent": "souther",
        "to_agent": "yuko",
        "content": "ふん、認めよう",
        "message_type": "memory_approval",
        "task_id": case_id,
    }
    result = await iw.process_memory_approval(msg)
    assert result["action"] == "skipped"
    assert result["reason"] == "proposal_missing"
