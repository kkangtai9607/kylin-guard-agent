from backend.app.agent.planning import Planner
from backend.app.llm.provider import UnavailableLLMProvider
from backend.app.mcp_client.client import KylinGuardMCPClient
from mcp_server.registry import ToolRegistry


def test_cleanup_intent_is_deterministic_read_only_analysis() -> None:
    mcp = KylinGuardMCPClient(ToolRegistry.for_mode("READ_ONLY"))
    plan = Planner(UnavailableLLMProvider(), mcp).plan("请帮我清理系统垃圾和旧日志")
    assert plan.intent.value == "CLEANUP"
    assert plan.steps[0].tool_name == "large_file_scan"
    assert plan.steps[0].arguments["path"] == "__cleanup_roots__"
    assert plan.requires_approval is False
    assert plan.risk_level == "L2"


def test_cleanup_synonyms_route_to_candidate_scan() -> None:
    for goal in ("分析旧日志", "检查缓存垃圾", "cleanup old logs"):
        intent, complexity, tool = Planner.route(goal)
        assert intent.value == "CLEANUP"
        assert complexity.value == "COMPLEX"
        assert tool == "large_file_scan"
