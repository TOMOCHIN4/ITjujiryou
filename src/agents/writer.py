from src.agents.base import AGENT_TOOLS, load_prompt


def build_writer_options() -> dict:
    return {
        "system_prompt": load_prompt("writer"),
        "allowed_tools": list(AGENT_TOOLS["writer"]),
    }
