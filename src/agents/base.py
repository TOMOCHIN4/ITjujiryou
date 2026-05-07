"""エージェント基底: prompt 読み込み、ツール権限テーブル、ClaudeAgentOptions ビルダ。

各エージェントの allowed_tools / model / effort はここで一元管理する。
サウザー化（社長が実務ツールを持つこと）を防ぐコード上の砦。
"""
from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"

# MCP サーバ名と各カスタムツールの完全修飾名
MCP_SERVER_NAME = "itjujiryou"

# モデル: 5人とも Opus 4.7。env で個別上書き可
# 例: ITJUJIRYOU_MODEL_SOUTHER=claude-sonnet-4-6
DEFAULT_MODEL = "claude-opus-4-7"
AGENT_MODEL: dict[str, str] = {
    "souther": DEFAULT_MODEL,
    "yuko":    DEFAULT_MODEL,
    "designer": DEFAULT_MODEL,
    "engineer": DEFAULT_MODEL,
    "writer":   DEFAULT_MODEL,
}

# Thinking effort: ユウコ xhigh、他 high。env で個別上書き可
# 例: ITJUJIRYOU_EFFORT_SOUTHER=xhigh
# SDK 0.1.76+ の effort は "low" | "medium" | "high" | "xhigh" | "max"
AGENT_EFFORT: dict[str, str] = {
    "souther":  "high",
    "yuko":     "xhigh",
    "designer": "high",
    "engineer": "high",
    "writer":   "high",
}


def _resolve_model(agent: str) -> str:
    return os.environ.get(f"ITJUJIRYOU_MODEL_{agent.upper()}", AGENT_MODEL[agent])


def _resolve_effort(agent: str) -> str:
    return os.environ.get(f"ITJUJIRYOU_EFFORT_{agent.upper()}", AGENT_EFFORT[agent])


def mcp_tool(name: str) -> str:
    return f"mcp__{MCP_SERVER_NAME}__{name}"


# 各エージェントのツール権限。ここが PLAN.md §10.1 サウザー化防止の要。
AGENT_TOOLS: dict[str, list[str]] = {
    "souther": [
        mcp_tool("send_message"),
        mcp_tool("read_status"),
        "Read",
    ],
    "yuko": [
        mcp_tool("send_message"),
        mcp_tool("dispatch_task"),
        mcp_tool("propose_plan"),
        mcp_tool("evaluate_deliverable"),
        mcp_tool("update_status"),
        mcp_tool("read_status"),
        mcp_tool("deliver"),
        "Read",
        "Write",
    ],
    "designer": [
        mcp_tool("send_message"),
        mcp_tool("read_status"),
        mcp_tool("update_status"),
        mcp_tool("consult_peer"),
        "Read",
        "Write",
        "Edit",
        "Bash",
        "WebSearch",
    ],
    "engineer": [
        mcp_tool("send_message"),
        mcp_tool("read_status"),
        mcp_tool("update_status"),
        mcp_tool("consult_peer"),
        "Read",
        "Write",
        "Edit",
        "Bash",
        "WebSearch",
        "WebFetch",
    ],
    "writer": [
        mcp_tool("send_message"),
        mcp_tool("read_status"),
        mcp_tool("update_status"),
        mcp_tool("consult_peer"),
        "Read",
        "Write",
        "Edit",
        "WebSearch",
        "WebFetch",
    ],
}

PROMPT_FILES = {
    "souther": "souther_president.md",
    "yuko": "yuko_secretary.md",
    "designer": "designer.md",
    "engineer": "engineer.md",
    "writer": "writer.md",
}


def _extract_souther_quotes(text: str) -> list[tuple[int, str]]:
    """`### N.【場面タグ】` で始まる名台詞ブロックを (番号, 本文) で切り出す。"""
    parts = re.split(r"\n(?=### \d+\.)", text)
    out: list[tuple[int, str]] = []
    for p in parts:
        m = re.match(r"### (\d+)\.", p)
        if m:
            out.append((int(m.group(1)), p.strip()))
    return out


SPOTLIGHT_LOG = REPO_ROOT / "data" / "logs" / "souther_spotlight.log"
SOUTHER_STATE_PATH = REPO_ROOT / "data" / "logs" / "souther_state.json"

# Python 確率制御モード（プロンプト内の「5〜10案件に1度」のような頻度指示は
# LLM が状態保持できないため、Python 側で決定的に発火判定する）
SOUTHER_MODES: dict[str, dict[str, float | int]] = {
    "深い独白": {"probability": 1 / 30, "cooldown": 15, "priority": 1},
    "説き諭し": {"probability": 1 / 7,  "cooldown": 4,  "priority": 2},
    "亀裂":     {"probability": 1 / 7,  "cooldown": 4,  "priority": 3},
    "強がり":   {"probability": 1 / 5,  "cooldown": 3,  "priority": 4},
}

_SOUTHER_MODE_BLOCKS: dict[str, str] = {
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


def _load_souther_state() -> dict:
    if not SOUTHER_STATE_PATH.exists():
        return {"total": 0, "last_fire": {}}
    try:
        return json.loads(SOUTHER_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"total": 0, "last_fire": {}}


def _save_souther_state(state: dict) -> None:
    try:
        SOUTHER_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SOUTHER_STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _decide_souther_mode() -> Optional[str]:
    """召喚ごとに発火モードを決定。

    優先度順に評価し、確率＋cooldown を満たした中で最も優先度の高いものを採用。
    どれも発火しなかった場合は None（通常モード）。

    環境変数 ``ITJUJIRYOU_FORCE_MODE`` が設定されていればそれを強制発火する
    （テスト・実演用）。
    """
    forced = os.environ.get("ITJUJIRYOU_FORCE_MODE", "").strip()
    state = _load_souther_state()
    state["total"] = int(state.get("total", 0)) + 1
    n = state["total"]
    last_fire = state.setdefault("last_fire", {})

    if forced:
        if forced in SOUTHER_MODES or forced == "通常":
            if forced != "通常":
                last_fire[forced] = n
            _save_souther_state(state)
            return forced if forced != "通常" else None

    fired: list[tuple[int, str]] = []
    for mode, cfg in SOUTHER_MODES.items():
        last = int(last_fire.get(mode, 0))
        if n - last < int(cfg["cooldown"]):
            continue
        if random.random() < float(cfg["probability"]):
            fired.append((int(cfg["priority"]), mode))
            last_fire[mode] = n
    _save_souther_state(state)

    if not fired:
        return None
    fired.sort()  # priority 昇順 = 高優先度が先
    return fired[0][1]


def _souther_mode_block(mode: str) -> str:
    return "\n\n---\n\n" + _SOUTHER_MODE_BLOCKS[mode]


def _log_souther_mode(mode: Optional[str]) -> None:
    """spotlight.log に併記する（召喚順とモード発火を時系列で追える）。"""
    try:
        SPOTLIGHT_LOG.parent.mkdir(parents=True, exist_ok=True)
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        with SPOTLIGHT_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] mode={mode or '通常'}\n")
    except OSError:
        pass


def _spotlight_block(quotes_text: str, k: int = 3) -> str:
    """21選から k 件をランダムに選び「今回の召喚で念頭に置く三選」セクションを返す。

    選ばれた台詞番号を data/logs/souther_spotlight.log に1行追記する（観測用）。
    """
    items = _extract_souther_quotes(quotes_text)
    if len(items) < k:
        return ""
    picks = random.sample(items, k)
    header = (
        "## 今回の召喚で念頭に置く三選\n\n"
        "以下の三節を**この応答の軸**として、場面タグの精神を汲んで変奏せよ。"
        "毎回同じ台詞を反復するな。案件の性質に応じて引き、必要なら一節だけ取って一句に編め。\n\n"
    )
    body = "\n\n---\n\n" + header + "\n\n".join(text for _, text in picks)
    try:
        SPOTLIGHT_LOG.parent.mkdir(parents=True, exist_ok=True)
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).isoformat()
        with SPOTLIGHT_LOG.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] picks={[n for n, _ in picks]}\n")
    except OSError:
        pass
    return body


def load_prompt(agent: str) -> str:
    fname = PROMPT_FILES[agent]
    body = (PROMPTS_DIR / fname).read_text(encoding="utf-8")
    # 全員に社訓を自動連結
    motto_path = PROMPTS_DIR / "_company_motto.md"
    if motto_path.exists():
        body = body + "\n\n---\n\n" + motto_path.read_text(encoding="utf-8")
    # 社長は名台詞集 + 召喚ごとのスポットライト3選 + Python 確率制御モード
    if agent == "souther":
        quotes_path = PROMPTS_DIR / "souther_quotes.md"
        if quotes_path.exists():
            quotes_text = quotes_path.read_text(encoding="utf-8")
            body = body + "\n\n---\n\n" + quotes_text + _spotlight_block(quotes_text)
        mode = _decide_souther_mode()
        _log_souther_mode(mode)
        if mode is not None:
            body = body + _souther_mode_block(mode)
    return body


def build_agent_options(agent: str, mcp_server) -> "object":
    """ClaudeAgentOptions を構築して返す。

    `mcp_server` は create_sdk_mcp_server() で作った SDK MCP サーバオブジェクト。
    """
    from claude_agent_sdk import ClaudeAgentOptions  # 遅延 import

    return ClaudeAgentOptions(
        system_prompt=load_prompt(agent),
        allowed_tools=AGENT_TOOLS[agent],
        mcp_servers={MCP_SERVER_NAME: mcp_server},
        permission_mode="bypassPermissions",
        model=_resolve_model(agent),
        effort=_resolve_effort(agent),
    )


async def run_agent(
    agent: str,
    user_message: str,
    mcp_server,
    task_id: Optional[str] = None,
) -> str:
    """エージェントを起動し、最終的なテキスト応答を返す。"""
    from claude_agent_sdk import ClaudeSDKClient

    from src.events.logger import log

    options = build_agent_options(agent, mcp_server)
    final_text_chunks: list[str] = []

    await log(agent, "起動", event_type="agent_start", task_id=task_id, print_stdout=False)

    async with ClaudeSDKClient(options=options) as client:
        await client.query(user_message)
        async for msg in client.receive_response():
            # AssistantMessage に含まれる TextBlock を集める
            content = getattr(msg, "content", None)
            if content:
                for block in content:
                    text = getattr(block, "text", None)
                    if text:
                        final_text_chunks.append(text)
                        await log(
                            agent,
                            text[:200] + ("…" if len(text) > 200 else ""),
                            event_type="thinking",
                            task_id=task_id,
                        )
                    tool_name = getattr(block, "name", None)
                    if tool_name:
                        await log(
                            agent,
                            f"tool_use: {tool_name}",
                            event_type="tool_use",
                            task_id=task_id,
                            details={"tool": tool_name},
                        )

    return "\n".join(final_text_chunks).strip()
