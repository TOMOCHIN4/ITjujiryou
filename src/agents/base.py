"""エージェント基底: prompt 読み込み、ツール権限テーブル、ClaudeAgentOptions ビルダ。

各エージェントの allowed_tools / model / effort はここで一元管理する。
サウザー化（社長が実務ツールを持つこと）を防ぐコード上の砦。
"""
from __future__ import annotations

import os
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
    "souther":  "medium",
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


def load_prompt(agent: str) -> str:
    fname = PROMPT_FILES[agent]
    body = (PROMPTS_DIR / fname).read_text(encoding="utf-8")
    # 全員に社訓を自動連結
    motto_path = PROMPTS_DIR / "_company_motto.md"
    if motto_path.exists():
        body = body + "\n\n---\n\n" + motto_path.read_text(encoding="utf-8")
    # 社長は名台詞集も自動連結
    if agent == "souther":
        quotes_path = PROMPTS_DIR / "souther_quotes.md"
        if quotes_path.exists():
            body = body + "\n\n---\n\n" + quotes_path.read_text(encoding="utf-8")
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
