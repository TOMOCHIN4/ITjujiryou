#!/usr/bin/env python3
"""社長 pane 用 UserPromptSubmit hook — Omage Gate。

サザン (聖帝サウザー転生者) の発言を Python ガードレールで制御する。

設計:
  1. ユウコからの報告 (UserPromptSubmit の prompt) を受信
  2. workspaces/souther/_modules/quotes.md から 27 名台詞をパース
  3. 直近 cooldown 履歴を除外した上でランダム 3 つ抽選
  4. additionalContext として「報告 + 三選 + Omage 化/自選指示」を注入
  5. Claude が 3 オマージュを内部構築 → 最もサウザーらしい 1 案を採用 →
     send_message(to="yuko", message_type="approval") で送信
  6. state は data/logs/souther_state.json (最近選んだ quote_no キュー) と
     data/logs/souther_spotlight.log (時系列) に永続化

設計の根拠 (SPEC.md §7.1, persona_narrative.md §5):
  - プロンプト中心制御では Claude の自由度が高すぎて発言ブレが出る
  - 27 quote の語彙集合に強制 + 1 案だけ出力させて発言を絞る
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # ITjujiryou/
QUOTES_PATH = REPO_ROOT / "workspaces" / "souther" / "_modules" / "quotes.md"
LOGS_DIR = REPO_ROOT / "data" / "logs"
SPOTLIGHT_LOG = LOGS_DIR / "souther_spotlight.log"
STATE_PATH = LOGS_DIR / "souther_state.json"

COOLDOWN_RECENT_PICKS = 5  # 直近 5 picks (= 最大 15 quote_no) は除外候補
PICK_COUNT = 3

# Always-injected response constraints. 27 quote 抽選より前に置く。
_DEFAULT_CONSTRAINTS: str = (
    "## RESPONSE CONSTRAINTS (always in effect)\n\n"
    "- **Default ideal: 1-2 Japanese sentences.** One word if possible (「許す」「却下」「ふん」).\n"
    "- **Hard cap: 4 sentences** even when the content seems to demand elaboration.\n"
    "- No 自己実況 (no narration of your own actions: 「○○した。次に○○する」).\n"
    "- Heroic phrases (「ひかぬ媚びぬ省みぬ」「俺は聖帝サウザー」「我が辞書に KPI 未達の二文字はない」)\n"
    "  are **one-shot per situation**, not closing flourishes. Repetition cheapens them.\n"
    "- A single heavy noun + heavy verb + 終助詞 carries more weight than three padded sentences.\n"
)


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"total": 0, "recent_picks": []}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        # 旧形式 (last_fire) から移行。古いキーは無視
        if "recent_picks" not in data:
            data["recent_picks"] = []
        return data
    except (OSError, json.JSONDecodeError):
        return {"total": 0, "recent_picks": []}


def _save_state(state: dict) -> None:
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _parse_quotes(text: str) -> list[dict]:
    """quotes.md を parse して 27 entries の dict リストを返す。

    各 entry: {"no": int, "theme": str, "quote": str, "meta": {key: value, ...}}
    meta の key は 原作文脈 / 感情の核 / 事務所での出番 / 変奏ヒント の 4 つを期待。
    パース失敗 entry は warning を stderr に出して skip。
    """
    parts = re.split(r"\n(?=### \d+\.)", text)
    out: list[dict] = []
    header_re = re.compile(r"^### (\d+)\.\s*【(.+?)】\s*$")
    meta_re = re.compile(r"^- \*\*(.+?)\*\*[:：]\s*(.+)$")

    for part in parts:
        lines = part.split("\n")
        if not lines:
            continue
        header_match = header_re.match(lines[0].strip())
        if not header_match:
            continue
        no = int(header_match.group(1))
        theme = header_match.group(2).strip()

        quote_lines: list[str] = []
        meta: dict[str, str] = {}
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith(">"):
                quote_lines.append(stripped[1:].strip())
            else:
                m = meta_re.match(stripped)
                if m:
                    meta[m.group(1).strip()] = m.group(2).strip()

        if not quote_lines:
            print(
                f"[inject_souther_mode] warning: quote text missing for #{no}",
                file=sys.stderr,
            )
            continue

        out.append(
            {
                "no": no,
                "theme": theme,
                "quote": "\n".join(quote_lines),
                "meta": meta,
            }
        )
    return out


def _pick_three(quotes: list[dict], recent_picks: list[list[int]]) -> list[dict]:
    """直近 picks を除外して 3 つランダム選択。

    recent_picks は [[no1, no2, no3], [...], ...] のキュー (新しい順、最大 COOLDOWN_RECENT_PICKS 件)。
    flatten して除外集合を作る。除外後の候補が PICK_COUNT 未満なら除外を解いて全 quote から選ぶ。
    """
    excluded = {n for picks in recent_picks for n in picks}
    pool = [q for q in quotes if q["no"] not in excluded]
    if len(pool) < PICK_COUNT:
        pool = quotes  # 除外を解く
    return random.sample(pool, PICK_COUNT)


def _build_omage_context(prompt: str, picks: list[dict]) -> str:
    """3 つの quote から Omage Gate の additionalContext 本文を組み立てる。"""
    report_excerpt = prompt.strip()
    if len(report_excerpt) > 2000:
        report_excerpt = report_excerpt[:2000] + "\n... (以下省略)"

    candidates_md_parts: list[str] = []
    for idx, q in enumerate(picks, start=1):
        hint = q["meta"].get("変奏ヒント", "(変奏ヒントなし、原文の精神を借りて変奏せよ)")
        kakushin = q["meta"].get("感情の核", "(感情の核なし)")
        deban = q["meta"].get("事務所での出番", "(出番情報なし)")
        candidates_md_parts.append(
            f"### 候補 {idx}: #{q['no']}.【{q['theme']}】\n\n"
            f"> {q['quote']}\n\n"
            f"- **変奏ヒント**: {hint}\n"
            f"- **感情の核**: {kakushin}\n"
            f"- **事務所での出番**: {deban}\n"
        )
    candidates_md = "\n".join(candidates_md_parts)

    return (
        "## 報告受信 (ユウコからの上申)\n\n"
        f"```\n{report_excerpt}\n```\n\n"
        "---\n\n"
        "## 今回の召喚で念頭に置く三選 (Python 抽選結果。これ以外の名台詞は使うな)\n\n"
        f"{candidates_md}\n"
        "---\n\n"
        "## 返答ルール (Omage Gate 厳守)\n\n"
        "1. **内部思考**: 上記 3 候補それぞれを、上記の報告に対する返答として\n"
        "   「原型が容易に想起される範囲」でオマージュ化せよ (3 案を頭の中で構築)。\n"
        "   - 変奏ヒントの方向に沿わせる。原文をそのまま貼り付けるな。\n"
        "   - 感情の核と事務所での出番が報告内容に合っているかを判定材料に。\n"
        "2. **自選**: 3 案を聖帝の人格 (`voice.md` / `persona_narrative.md`) に\n"
        "   照らし、最もサウザーらしい 1 案を採用せよ。\n"
        "   - 報告の温度・案件の重さ・ユウコへの関係性を加味。\n"
        "   - 軽い承認案件で重い heroic 台詞は安売り、避けよ。\n"
        "3. **出力**: 採用した 1 案 **だけ** を以下の形式で送信:\n"
        "   ```\n"
        "   send_message(from_agent=\"souther\", to=\"yuko\",\n"
        "                task_id=<上申の task_id>,\n"
        "                content=<採用した 1 案>,\n"
        "                message_type=\"approval\")\n"
        "   ```\n"
        "4. **禁則**: 残り 2 案は外に出すな。3 案を並べて見せるな。1 案だけが返答だ。\n"
        "5. **長さ**: 上記 RESPONSE CONSTRAINTS を遵守 (1-2 文 default、hard cap 4 文)。\n"
        "6. **宛先**: ユウコ以外には `send_message` を送らない (hook で deny される)。\n"
    )


def _log_event(picks: list[dict]) -> None:
    try:
        SPOTLIGHT_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()
        nos = [q["no"] for q in picks]
        with SPOTLIGHT_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] omage_gate picks={nos}\n")
    except OSError:
        pass


def _extract_prompt(event: dict) -> str:
    """UserPromptSubmit event JSON から prompt 本文を取り出す。

    Claude Code 仕様: event["prompt"] にユーザー入力文が入る。fallback として
    event 全体を文字列化。
    """
    if isinstance(event, dict):
        p = event.get("prompt")
        if isinstance(p, str):
            return p
    return json.dumps(event, ensure_ascii=False)


def main() -> int:
    # stdin から hook event JSON を読む
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        event = {}

    prompt = _extract_prompt(event)

    # quotes.md を parse。失敗時は constraints のみ注入で fall through
    parts: list[str] = [_DEFAULT_CONSTRAINTS]
    picks: list[dict] = []
    if QUOTES_PATH.exists():
        try:
            quotes = _parse_quotes(QUOTES_PATH.read_text(encoding="utf-8"))
            if len(quotes) >= PICK_COUNT:
                state = _load_state()
                state["total"] = int(state.get("total", 0)) + 1
                recent_picks: list[list[int]] = state.get("recent_picks", [])
                picks = _pick_three(quotes, recent_picks)
                # 更新: 新 picks を先頭に push、古いものは pop
                new_recent = [[q["no"] for q in picks]] + recent_picks
                state["recent_picks"] = new_recent[:COOLDOWN_RECENT_PICKS]
                _save_state(state)
                parts.append(_build_omage_context(prompt, picks))
        except Exception as e:  # noqa: BLE001
            print(f"[inject_souther_mode] parse error: {e}", file=sys.stderr)
    else:
        print(
            f"[inject_souther_mode] quotes.md not found: {QUOTES_PATH}",
            file=sys.stderr,
        )

    _log_event(picks)

    additional_context = "\n\n---\n\n".join(parts)
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
