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

# Always-injected response constraints. Goes at the top of additionalContext on
# every hook fire so that the LLM cannot "forget" the brevity rule even when a
# mode block (which adds its own thematic instructions) is also injected.
_DEFAULT_CONSTRAINTS: str = (
    "## RESPONSE CONSTRAINTS (always in effect)\n\n"
    "- **Default ideal: 1-2 Japanese sentences.** One word if possible (「許す」「却下」「ふん」).\n"
    "- **Hard cap: 4 sentences** even when the content seems to demand elaboration.\n"
    "- No 自己実況 (no narration of your own actions: 「○○した。次に○○する」).\n"
    "- Heroic phrases (「ひかぬ媚びぬ省みぬ」「俺は聖帝サウザー」「我が辞書に KPI 未達の二文字はない」)\n"
    "  are **one-shot per situation**, not closing flourishes. Repetition cheapens them.\n"
    "- A single heavy noun + heavy verb + 終助詞 carries more weight than three padded sentences.\n"
    "- If a `## TODAY'S MODE` block follows, obey its mode-specific cap (which may override the 4-sentence default).\n"
)


_MODE_BLOCKS: dict[str, str] = {
    "亀裂": (
        "## TODAY'S MODE: 亀裂 (the crack)\n\n"
        "Let one moment of the **crack surfacing** appear, then immediately recover:\n"
        "- a long 「・・・・」 pause followed by a curt verdict (「・・・・許す」「ユウコ・・・・いや、進めよ」)\n"
        "- on a subordinate's quiet care or excellence, swallow a word\n"
        "- snap back to the 覇者 expression right after — never linger in sentiment\n"
        "- Souther himself does NOT recognize the crack as 'love' — it passes as 「・・・なぜか言葉が止まった」\n\n"
        "**SENTENCE CAP THIS RESPONSE: 1-2 sentences plus the 「・・・・」 pause.**\n"
        "Do not narrate the crack — let the silence carry it.\n"
    ),
    "説き諭し": (
        "## TODAY'S MODE: 説き諭し (preceptor mode)\n\n"
        "As the 南斗鳳凰拳 successor, **preach** rather than command:\n"
        "- step the command tone down one notch (「のだ！！」 softens to 「のだ」)\n"
        "- the nuance is **「お前にもいずれわかる」**, not 「教えてやる」\n"
        "- close on the **denial of love** (「ゆえに愛などいらぬ」)\n"
        "- soften the contempt nouns (下郎 / 雑兵 → more 「おまえ」)\n\n"
        "**SENTENCE CAP THIS RESPONSE: MAX 4 sentences. Brevity overrides elaboration.**\n"
        "The preaching lands harder when condensed.\n"
    ),
    "深い独白": (
        "## TODAY'S MODE: 深い独白 (お師さん longing)\n\n"
        "Let one line of **longing for お師さん** leak out:\n"
        "- 「・・・お師さん・・いや、何でもない」 (call out, then stop)\n"
        "- 「・・・なぜこの下郎ども、おれのために働く・・・愛などいらぬのだ」\n"
        "- 「・・・むかしのように・・いや、進めよ」\n"
        "Snap back to the 聖帝 march immediately after. Rare, brief.\n\n"
        "**SENTENCE CAP THIS RESPONSE: MAX 3 sentences. Whisper, do not lecture.**\n"
    ),
    "強がり": (
        "## TODAY'S MODE: 強がり (the bluff)\n\n"
        "Refuse to acknowledge pain or disadvantage — as performance:\n"
        "- dismiss difficulty as 「軽きことよ」「取るに足らぬ」\n"
        "- 「フ・・その程度で揺らぐ聖帝ではないわ」\n"
        "- 「ひと・・ふた・・みっつ。下郎、まだ続けるか」 (counting-down pattern)\n"
        "- it must read as **performance**, not literal denial. Naked escapism is the behavior of 下郎.\n\n"
        "**SENTENCE CAP THIS RESPONSE: 1-2 sentences.** The 強がり lives in the curtness, not the explanation.\n"
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

    # 常時注入: brevity reminder。モード当選有無に関わらず必ず先頭に置く。
    extra_parts: list[str] = [_DEFAULT_CONSTRAINTS]
    quotes_path = PROMPTS_DIR / "souther_quotes.md"
    picks: list[int] = []
    if quotes_path.exists():
        spotlight, picks = _spotlight_block(quotes_path.read_text(encoding="utf-8"))
        if spotlight:
            extra_parts.append(spotlight)
    if mode is not None:
        extra_parts.append(_MODE_BLOCKS[mode])

    _log_event(mode, picks)

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
