"""社長サウザー。実務ツールを物理的に持たない。"""
from src.agents.base import AGENT_TOOLS, load_prompt


def build_president_options() -> dict:
    """テスト用に allowed_tools を含む辞書を返す。"""
    return {
        "system_prompt": load_prompt("souther"),
        "allowed_tools": list(AGENT_TOOLS["souther"]),
    }
