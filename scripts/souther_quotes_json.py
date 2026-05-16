#!/usr/bin/env python3
"""souther-omage subagent 用 名台詞リスト出力ヘルパー。

quotes.md (27 名台詞) を全件 slim 化して JSON 配列で stdout に出す。
ランダム抽選は subagent 側でユウコの入力を踏まえて場面マッチング判定を行うため、
スクリプトは選別をせず全件を渡す。

本家 inject_souther_mode.py の cooldown state (data/logs/souther_state.json) は
一切読み書きしない (stateless 設計)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "hooks"))
from inject_souther_mode import QUOTES_PATH, _parse_quotes  # noqa: E402

# subagent に渡す meta フィールドの絞り込み。
# 「事務所での出番」「変奏ヒント」は subagent の判断に不要なため除外する。
META_KEEP = ("原作文脈", "感情の核")


def _slim(entry: dict) -> dict:
    meta = entry.get("meta", {})
    slim_meta = {k: meta[k] for k in META_KEEP if k in meta}
    return {
        "no": entry["no"],
        "theme": entry["theme"],
        "quote": entry["quote"],
        "meta": slim_meta,
    }


def main() -> int:
    try:
        text = QUOTES_PATH.read_text(encoding="utf-8")
    except OSError as e:
        json.dump({"error": f"quotes.md read failed: {e}"}, sys.stdout, ensure_ascii=False)
        return 1

    quotes = _parse_quotes(text)
    if not quotes:
        json.dump({"error": "no quotes parsed"}, sys.stdout, ensure_ascii=False)
        return 1

    json.dump([_slim(q) for q in quotes], sys.stdout, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
