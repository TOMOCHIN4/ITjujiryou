"""エージェント基底: prompt 読み込み、ツール権限テーブル、ClaudeAgentOptions ビルダ。

各エージェントの allowed_tools / model / effort はここで一元管理する。
サウザー化（社長が実務ツールを持つこと）を防ぐコード上の砦。
"""
from __future__ import annotations

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

# Thinking effort: ユウコ high、他 medium。env で個別上書き可
# 例: ITJUJIRYOU_EFFORT_SOUTHER=high
AGENT_EFFORT: dict[str, str] = {
    "souther":  "high",
    "yuko":     "high",
    "designer": "medium",
    "engineer": "medium",
    "writer":   "medium",
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
    # 社長は名台詞集 + 召喚ごとのスポットライト3選
    if agent == "souther":
        quotes_path = PROMPTS_DIR / "souther_quotes.md"
        if quotes_path.exists():
            quotes_text = quotes_path.read_text(encoding="utf-8")
            body = body + "\n\n---\n\n" + quotes_text + _spotlight_block(quotes_text)
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
