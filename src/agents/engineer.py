from src.agents.base import AGENT_TOOLS, load_prompt


def build_engineer_options() -> dict:
    return {
        "system_prompt": load_prompt("engineer"),
        "allowed_tools": list(AGENT_TOOLS["engineer"]),
    }
