#!/usr/bin/env python3
"""社長 pane 用 UserPromptSubmit hook (v2 二重構造の裏側、骨格のみ)。

Phase 1 のスコープは「指示理解・ディスパッチ雛型」まで。
ユウコからの新着上申のタイプ (P1 新規受注 / P2 値引き裁定 / P3 品質迷い / P4 発注取消)
を SQLite から lookup して判定し、`## INCOMING REQUEST TYPE` ラベルを
`additionalContext` に注入する **だけ**。

実 HOOK 処理 (`benchmarks/souther_hook_inventory.md` §3 の P1〜P7 サブ動作 — 履歴記録、
キーワード抽出、JSONL append, _last_write.log への timestamp 書込 等) は **Phase 4 で本実装**。
本ファイルでは **NOOP** に留める。

v1 の `inject_souther_mode.py` (確率発火モード注入 + brevity 強制) は D17 で退役し、
本ファイルがその後継だが、目的が違う:
- 旧 (退役済): 応答スタイルの強制 (BREVITY / 4 モード)
- 新 (この骨格): 案件種別の文脈ラベリングのみ。応答スタイルはペルソナ (CLAUDE.md + _modules)
  に任せる
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]  # ITjujiryou/
DB_PATH = REPO_ROOT / "data" / "office.db"


# v2: メッセージ本文からタイプを推定するキーワード辞書。
# `benchmarks/souther_hook_inventory.md` の P1〜P4 分類に対応。
# 単純な正規表現で構わない (Phase 1 骨格)。誤判定しても応答スタイルに副作用は無い。
_TYPE_PATTERNS: dict[str, list[str]] = {
    "P2_DISCOUNT": [
        r"値引き",
        r"半額",
        r"\d+\s*%\s*(?:off|オフ|引き)",
        r"単価.*下げ",
    ],
    "P4_CANCELLATION": [
        r"発注取消",
        r"取消",
        r"キャンセル",
        r"中止",
    ],
    "P3_QUALITY_ESCALATION": [
        r"escalate",
        r"品質.*迷",
        r"判断.*仰",
        r"最終決裁",
        r"納品前.*ご相談",
    ],
    "P1_NEW_ORDER": [
        r"新規.*ご相談",
        r"新規案件",
        r"ご相談です",
    ],
}


def _read_task_id_from_stdin() -> Optional[str]:
    """hook event JSON の中から task_id 候補を抽出する。

    Claude Code は UserPromptSubmit hook に stdin 経由で event JSON を渡す。
    そのプロンプト本文に「task_id: <uuid>」が含まれていれば task_id を返す。
    なければ None。
    """
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw:
        return None
    # event JSON or plain prompt text どちらでも対応
    m = re.search(
        r"task_id[:\s]+([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        raw,
    )
    return m.group(1) if m else None


def _fetch_latest_approval_request_content(task_id: str) -> Optional[str]:
    """ユウコ → サザン宛の最新 approval_request メッセージ本文を取得する。

    Phase 1 では「直近の上申本文」を 1 件読むだけ。複数本文を集約する処理は Phase 4。
    """
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=2.0)
    except sqlite3.OperationalError:
        return None
    try:
        cur = conn.execute(
            """
            SELECT content
            FROM messages
            WHERE task_id = ?
              AND from_agent = 'yuko'
              AND to_agent = 'souther'
              AND message_type = 'approval_request'
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (task_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _classify(content: str) -> str:
    """メッセージ本文から request type を判定する。最初に一致した type を返す。"""
    for type_label, patterns in _TYPE_PATTERNS.items():
        for p in patterns:
            if re.search(p, content, flags=re.IGNORECASE):
                return type_label
    return "UNKNOWN"


def _label_block(type_label: str) -> str:
    """ペルソナを縛らない軽量な文脈ラベルブロックを生成する。"""
    descriptions = {
        "P1_NEW_ORDER": "新規案件の受注承認上申。儀礼応答で受任 (許す/進めよ) を返す",
        "P2_DISCOUNT": "値引き/単価裁定の上申。聖帝の『ひかぬ』の精神に照らして判断",
        "P3_QUALITY_ESCALATION": "品質基準で迷った成果物の上申。聖帝の眼で一刀の判定",
        "P4_CANCELLATION": "発注取消・粗品要求の対応。準備費回収、粗品提供は不可の方針",
        "UNKNOWN": "種別判定なし。ユウコ伝令本文をそのまま読み取って判断",
    }
    return (
        f"## INCOMING REQUEST TYPE: {type_label}\n\n"
        f"{descriptions.get(type_label, descriptions['UNKNOWN'])}\n\n"
        "**Phase 1 注**: 本ラベルは文脈参照のみ。儀礼応答のスタイル (聖帝口調・短さ) は "
        "ペルソナ (CLAUDE.md + _modules) の判断に任せる。応答スタイルは強制しない。"
    )


def main() -> int:
    task_id = _read_task_id_from_stdin()
    type_label = "UNKNOWN"
    if task_id:
        content = _fetch_latest_approval_request_content(task_id)
        if content:
            type_label = _classify(content)

    additional_context = _label_block(type_label)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
