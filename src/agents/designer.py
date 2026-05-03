from src.agents.base import AGENT_TOOLS, load_prompt


def build_designer_options() -> dict:
    return {
        "system_prompt": load_prompt("designer"),
        "allowed_tools": list(AGENT_TOOLS["designer"]),
    }
