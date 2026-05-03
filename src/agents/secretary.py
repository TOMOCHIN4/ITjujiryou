from src.agents.base import AGENT_TOOLS, load_prompt


def build_secretary_options() -> dict:
    return {
        "system_prompt": load_prompt("yuko"),
        "allowed_tools": list(AGENT_TOOLS["yuko"]),
    }
