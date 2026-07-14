import uuid

from backend.app.agent.planning import Planner
from backend.app.llm.provider import MockLLMProvider, UnavailableLLMProvider
from backend.app.mcp_client.client import KylinGuardMCPClient
from mcp_server.registry import ToolRegistry

DISK_CLEANUP_GOAL = (
    "\u5206\u6790\u5f53\u524d\u78c1\u76d8\u5360\u7528\uff0c"
    "\u7ed9\u51fa\u6839\u56e0\u548c\u53ef\u6e05\u7406\u5019\u9009"
)


def test_real_chinese_disk_cleanup_goal_uses_system_root_and_cleanup_roots() -> None:
    mcp = KylinGuardMCPClient(ToolRegistry.for_mode("READ_ONLY"))
    plan = Planner(UnavailableLLMProvider(), mcp).plan(DISK_CLEANUP_GOAL)

    assert [step.tool_name for step in plan.steps] == ["disk_usage_scan", "large_file_scan"]
    assert plan.steps[0].arguments == {"path": "/"}
    assert plan.steps[1].arguments == {"path": "__cleanup_roots__", "min_bytes": 10_000_000, "limit": 50}
    assert plan.intent.value == "CLEANUP"
    assert plan.risk_level == "L2"


def test_model_disk_path_is_normalized_before_execution() -> None:
    payload = {
        "plan_id": str(uuid.uuid4()),
        "user_goal": DISK_CLEANUP_GOAL,
        "intent": "CLEANUP",
        "complexity": "COMPLEX",
        "summary": "\u53ea\u8bfb\u5206\u6790\u78c1\u76d8\u5360\u7528\u548c\u6e05\u7406\u5019\u9009",
        "steps": [
            {
                "sequence": 1,
                "tool_name": "disk_usage_scan",
                "arguments": {"path": "/opt/kylin-guard"},
                "purpose": "\u67e5\u770b\u78c1\u76d8\u5360\u7528",
            },
            {
                "sequence": 2,
                "tool_name": "large_file_scan",
                "arguments": {"path": ".", "min_bytes": 1, "limit": 5},
                "purpose": "\u67e5\u770b\u6e05\u7406\u5019\u9009",
            },
        ],
        "expected_evidence": ["disk_usage_scan", "large_file_scan"],
        "risk_level": "L2",
        "requires_approval": False,
        "verification": "schema",
        "rollback": "not applicable",
        "public_reason": "\u4f7f\u7528\u53ea\u8bfb\u5de5\u5177\u5206\u6790\u3002",
    }
    mcp = KylinGuardMCPClient(ToolRegistry.for_mode("READ_ONLY"))
    plan = Planner(MockLLMProvider(payload), mcp).plan(DISK_CLEANUP_GOAL)

    assert plan.steps[0].arguments == {"path": "/"}
    assert plan.steps[1].arguments == {"path": "__cleanup_roots__", "min_bytes": 10_000_000, "limit": 50}


def test_real_chinese_network_status_routes_to_network_tools() -> None:
    mcp = KylinGuardMCPClient(ToolRegistry.for_mode("READ_ONLY"))
    goal = "\u67e5\u8be2\u7f51\u7edc\u72b6\u6001"

    plan = Planner(UnavailableLLMProvider(), mcp).plan(goal)

    assert [step.tool_name for step in plan.steps] == [
        "network_config_snapshot",
        "network_socket_list",
    ]
    assert plan.intent.value == "DIAGNOSIS"
    assert plan.risk_level == "L2"
