import uuid

from backend.app.agent.planning import Planner
from backend.app.llm.provider import MockLLMProvider, UnavailableLLMProvider
from backend.app.mcp_client.client import KylinGuardMCPClient
from mcp_server.registry import ToolRegistry


def test_real_chinese_disk_cleanup_goal_uses_system_root_and_cleanup_roots() -> None:
    mcp = KylinGuardMCPClient(ToolRegistry.for_mode("READ_ONLY"))
    plan = Planner(UnavailableLLMProvider(), mcp).plan("分析当前磁盘占用，给出根因和可清理候选")

    assert [step.tool_name for step in plan.steps] == ["disk_usage_scan", "large_file_scan"]
    assert plan.steps[0].arguments == {"path": "/"}
    assert plan.steps[1].arguments == {"path": "__cleanup_roots__", "min_bytes": 10_000_000, "limit": 50}
    assert plan.intent.value == "CLEANUP"
    assert plan.risk_level == "L2"


def test_model_disk_path_is_normalized_before_execution() -> None:
    goal = "分析当前磁盘占用，给出根因和可清理候选"
    payload = {
        "plan_id": str(uuid.uuid4()),
        "user_goal": goal,
        "intent": "CLEANUP",
        "complexity": "COMPLEX",
        "summary": "只读分析磁盘占用和清理候选",
        "steps": [
            {
                "sequence": 1,
                "tool_name": "disk_usage_scan",
                "arguments": {"path": "/opt/kylin-guard"},
                "purpose": "查看磁盘占用",
            },
            {
                "sequence": 2,
                "tool_name": "large_file_scan",
                "arguments": {"path": ".", "min_bytes": 1, "limit": 5},
                "purpose": "查看清理候选",
            },
        ],
        "expected_evidence": ["disk_usage_scan", "large_file_scan"],
        "risk_level": "L2",
        "requires_approval": False,
        "verification": "schema",
        "rollback": "not applicable",
        "public_reason": "使用只读工具分析。",
    }
    mcp = KylinGuardMCPClient(ToolRegistry.for_mode("READ_ONLY"))
    plan = Planner(MockLLMProvider(payload), mcp).plan(goal)

    assert plan.steps[0].arguments == {"path": "/"}
    assert plan.steps[1].arguments == {"path": "__cleanup_roots__", "min_bytes": 10_000_000, "limit": 50}
