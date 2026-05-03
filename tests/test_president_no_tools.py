"""社長サウザーが実務ツールを物理的に持たないこと（サウザー化防止）。"""
from src.agents.president import build_president_options
from src.agents.base import AGENT_TOOLS, mcp_tool


def test_president_has_no_implementation_tools():
    options = build_president_options()
    forbidden = ["Bash", "Edit", "Write", "WebSearch", "WebFetch"]
    for t in forbidden:
        assert t not in options["allowed_tools"], (
            f"社長が {t} を持っている。サウザー化のリスク。"
        )


def test_president_has_required_tools():
    options = build_president_options()
    assert mcp_tool("send_message") in options["allowed_tools"]
    assert mcp_tool("read_status") in options["allowed_tools"]
    assert "Read" in options["allowed_tools"]


def test_president_cannot_dispatch_or_deliver():
    """dispatch_task と deliver はユウコ専用であり、社長は持ってはいけない。"""
    tools = AGENT_TOOLS["souther"]
    assert mcp_tool("dispatch_task") not in tools
    assert mcp_tool("deliver") not in tools


def test_subordinates_cannot_dispatch_or_deliver():
    for agent in ("designer", "engineer", "writer"):
        tools = AGENT_TOOLS[agent]
        assert mcp_tool("dispatch_task") not in tools, f"{agent} が dispatch を持つ"
        assert mcp_tool("deliver") not in tools, f"{agent} が deliver を持つ"


def test_yuko_has_dispatch_and_deliver():
    tools = AGENT_TOOLS["yuko"]
    assert mcp_tool("dispatch_task") in tools
    assert mcp_tool("deliver") in tools


# --- Phase 1.5 追加 -------------------------------------------------------
def test_yuko_has_quality_loop_tools():
    tools = AGENT_TOOLS["yuko"]
    assert mcp_tool("propose_plan") in tools
    assert mcp_tool("evaluate_deliverable") in tools


def test_president_has_no_quality_loop_tools():
    tools = AGENT_TOOLS["souther"]
    for t in ("propose_plan", "evaluate_deliverable", "consult_peer", "deliver", "dispatch_task"):
        assert mcp_tool(t) not in tools, f"社長が {t} を持つ"


def test_subordinates_have_consult_peer():
    for agent in ("designer", "engineer", "writer"):
        assert mcp_tool("consult_peer") in AGENT_TOOLS[agent]


def test_subordinates_no_evaluate_or_propose():
    for agent in ("designer", "engineer", "writer"):
        tools = AGENT_TOOLS[agent]
        assert mcp_tool("evaluate_deliverable") not in tools
        assert mcp_tool("propose_plan") not in tools


def test_president_prompt_includes_quotes():
    """社長 prompt に名台詞集が連結されていること。"""
    from src.agents.base import load_prompt
    prompt = load_prompt("souther")
    # 代表的なキーフレーズをチェック
    keys = ["天空に極星はふたつはいらぬ", "敵はすべて下郎", "もう一度ぬくもりを"]
    for k in keys:
        assert k in prompt, f"名台詞 '{k}' が prompt に含まれていない"
