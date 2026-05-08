#!/usr/bin/env python3
"""社長 pane 用 UserPromptSubmit hook。

確率＋cooldown で「亀裂 / 説き諭し / 深い独白 / 強がり」モードを発火し、
名台詞21選から3選をランダムに選んで `additionalContext` として注入する。

src/agents/base.py から該当ロジックをマルチプロセス用に独立移植したもの。
状態は data/logs/souther_state.json (発火履歴) と
data/logs/souther_spotlight.log (時系列ログ) に永続化する。
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]  # ITjujiryou/
PROMPTS_DIR = REPO_ROOT / "prompts"
LOGS_DIR = REPO_ROOT / "data" / "logs"
SPOTLIGHT_LOG = LOGS_DIR / "souther_spotlight.log"
STATE_PATH = LOGS_DIR / "souther_state.json"

SOUTHER_MODES: dict[str, dict[str, float | int]] = {
    "深い独白": {"probability": 1 / 30, "cooldown": 15, "priority": 1},
    "説き諭し": {"probability": 1 / 7, "cooldown": 4, "priority": 2},
    "亀裂": {"probability": 1 / 7, "cooldown": 4, "priority": 3},
    "強がり": {"probability": 1 / 5, "cooldown": 3, "priority": 4},
}

_MODE_BLOCKS: dict[str, str] = {
    "亀裂": (
        "## 今回の召喚モード: 亀裂と揺らぎ\n\n"
        "応答のどこかに**亀裂が露出する瞬間**を含めよ:\n"
        "- 「・・・・」の長い間からの簡潔な裁定（「・・・・許す」「ユウコ・・・・いや、進めよ」）\n"
        "- 部下の細やかな配慮や卓越に、ふと言葉を呑み込む\n"
        "- 直後は**必ず覇者の表情に戻る**。湿っぽくしない\n"
        "- サウザー本人は亀裂を「自分の愛の流れ」と認識しない\n"
    ),
    "説き諭し": (
        "## 今回の召喚モード: 説き諭しモード\n\n"
        "南斗鳳凰拳の伝承者として、命令ではなく**説いて諭せ**:\n"
        "- 命令口調を一段降ろす（「のだ！！」を「のだ」程度に抑える）\n"
        "- 「教えてやる」ではなく「**お前にもいずれわかる**」のニュアンス\n"
        "- 結論は**愛の否定**で締める（「ゆえに愛などいらぬ」）\n"
        "- 部下を見下す呼称（下郎、雑兵）はやや控えめに（「おまえ」が増える）\n"
    ),
    "深い独白": (
        "## 今回の召喚モード: 深い独白（お師さん）\n\n"
        "応答のどこかに**お師さんへの渇望が滲む独白**を漏らせ:\n"
        "- 「・・・お師さん・・いや、何でもない」（呼びかけてやめる）\n"
        "- 「・・・なぜこの下郎ども、おれのために働く・・・愛などいらぬのだ」\n"
        "- 「・・・むかしのように・・いや、進めよ」\n"
        "**直後は必ず聖帝の歩みに戻る**。極稀な瞬間で、長く湿らせない。\n"
    ),
    "強がり": (
        "## 今回の召喚モード: 強がり（演技性）\n\n"
        "覇者として**痛みも不利も認めない演技**で応じよ:\n"
        "- 困難な案件を「軽きことよ」「取るに足らぬ」と一蹴\n"
        "- 「フ・・その程度で揺らぐ聖帝ではないわ」\n"
        "- 「ひと・・ふた・・みっつ。下郎、まだ続けるか」（数を数える型）\n"
        "- ただし**演技と分かる繊細さ**で。あからさまな逃避は下郎の振る舞い\n"
    ),
}


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"total": 0, "last_fire": {}}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"total": 0, "last_fire": {}}


def _save_state(state: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _decide_mode() -> Optional[str]:
    forced = os.environ.get("ITJUJIRYOU_FORCE_MODE", "").strip()
    state = _load_state()
    state["total"] = int(state.get("total", 0)) + 1
    n = state["total"]
    last_fire = state.setdefault("last_fire", {})

    if forced:
        if forced in SOUTHER_MODES or forced == "通常":
            if forced != "通常":
                last_fire[forced] = n
            _save_state(state)
            return forced if forced != "通常" else None

    fired: list[tuple[int, str]] = []
    for mode, cfg in SOUTHER_MODES.items():
        last = int(last_fire.get(mode, 0))
        if n - last < int(cfg["cooldown"]):
            continue
        if random.random() < float(cfg["probability"]):
            fired.append((int(cfg["priority"]), mode))
            last_fire[mode] = n
    _save_state(state)

    if not fired:
        return None
    fired.sort()
    return fired[0][1]


def _extract_quotes(text: str) -> list[tuple[int, str]]:
    parts = re.split(r"\n(?=### \d+\.)", text)
    out: list[tuple[int, str]] = []
    for p in parts:
        m = re.match(r"### (\d+)\.", p)
        if m:
            out.append((int(m.group(1)), p.strip()))
    return out


def _spotlight_block(quotes_text: str, k: int = 3) -> tuple[str, list[int]]:
    items = _extract_quotes(quotes_text)
    if len(items) < k:
        return "", []
    picks = random.sample(items, k)
    header = (
        "## 今回の召喚で念頭に置く三選\n\n"
        "以下の三節を**この応答の軸**として、場面タグの精神を汲んで変奏せよ。"
        "毎回同じ台詞を反復するな。案件の性質に応じて引き、必要なら一節だけ取って一句に編め。\n\n"
    )
    body = header + "\n\n".join(text for _, text in picks)
    return body, [n for n, _ in picks]


def _log_event(mode: Optional[str], picks: list[int]) -> None:
    try:
        SPOTLIGHT_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        with SPOTLIGHT_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] mode={mode or '通常'} picks={picks}\n")
    except OSError:
        pass


def main() -> int:
    # stdin から hook event JSON (使わなくても読み捨てる)
    try:
        sys.stdin.read()
    except Exception:
        pass

    mode = _decide_mode()

    extra_parts: list[str] = []
    quotes_path = PROMPTS_DIR / "souther_quotes.md"
    picks: list[int] = []
    if quotes_path.exists():
        spotlight, picks = _spotlight_block(quotes_path.read_text(encoding="utf-8"))
        if spotlight:
            extra_parts.append(spotlight)
    if mode is not None:
        extra_parts.append(_MODE_BLOCKS[mode])

    _log_event(mode, picks)

    if not extra_parts:
        return 0

    additional_context = "\n\n---\n\n".join(extra_parts)
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
