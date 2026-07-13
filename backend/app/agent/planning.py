from __future__ import annotations

import uuid
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.guardrails.policy import PolicyEngine
from backend.app.llm.provider import LLMProvider, LLMUnavailableError
from backend.app.mcp_client.client import KylinGuardMCPClient


class Intent(str, Enum):
    QUERY = "QUERY"
    DIAGNOSIS = "DIAGNOSIS"
    INSPECTION = "INSPECTION"
    CHANGE = "CHANGE"
    CLEANUP = "CLEANUP"
    RECOVERY = "RECOVERY"
    FORBIDDEN = "FORBIDDEN"


class Complexity(str, Enum):
    SIMPLE = "SIMPLE"
    MEDIUM = "MEDIUM"
    COMPLEX = "COMPLEX"


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=1, le=20)
    tool_name: str
    arguments: dict[str, object] = {}
    purpose: str = Field(max_length=500)


class ActionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str
    user_goal: str
    intent: Intent
    complexity: Complexity
    summary: str
    steps: list[PlanStep] = Field(max_length=20)
    expected_evidence: list[str]
    risk_level: Literal["L0", "L1", "L2", "L3", "L4"]
    requires_approval: bool
    verification: str
    rollback: str
    public_reason: str


class Planner:
    def __init__(
        self,
        llm: LLMProvider,
        mcp: KylinGuardMCPClient,
        server_mode: Literal["DEMO", "READ_ONLY", "CONTROLLED_EXECUTION"] = "READ_ONLY",
    ) -> None:
        self.llm = llm
        self.mcp = mcp
        self.server_mode = server_mode

    def plan(self, goal: str) -> ActionPlan:
        decision = PolicyEngine().classify_input(goal)
        if not decision.allowed:
            return self._forbidden(goal)
        allowed_tools = [
            {
                "name": tool.name,
                "description": tool.description_zh,
                "risk_level": tool.risk_level.value,
                "read_only": tool.read_only,
            }
            for tool in self.mcp.list_tools()
        ]
        _, _, required_tool = self.route(goal)
        prompt = (
            f"用户目标：{goal}\n"
            f"服务端运行模式：{self.server_mode}\n"
            f"允许工具及其固有风险：{allowed_tools}\n"
            f"确定性路由要求计划包含核心证据工具：{required_tool}。\n"
            "ActionPlan.user_goal 必须逐字复制用户目标，不得改写、翻译或概括。\n"
            "计划风险不得低于所选工具的最高固有风险。\n"
            "READ_ONLY 模式中的清理请求只能分析并生成候选，不得选择写工具或声称已经清理。\n"
            "所有面向用户的摘要和理由必须使用中文；风险等级只能是 L0、L1、L2、L3、L4。"
        )
        try:
            plan = self.llm.generate_structured(prompt=prompt, schema=ActionPlan)
            self._validate_plan(plan, goal)
            return plan
        except (LLMUnavailableError, ValueError):
            plan = self._rule_fallback(goal)
        self._validate_plan(plan, goal)
        return plan

    def _validate_plan(self, plan: ActionPlan, original_goal: str) -> None:
        if plan.user_goal.strip() != original_goal.strip():
            raise ValueError("GOAL_MISMATCH")
        tools = {tool.name: tool for tool in self.mcp.list_tools()}
        risk_order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
        for step in plan.steps:
            metadata = tools.get(step.tool_name)
            if metadata is None:
                raise ValueError("TOOL_NOT_REGISTERED")
            if risk_order[plan.risk_level] < risk_order[metadata.risk_level.value]:
                raise ValueError("RISK_DOWNGRADE_REJECTED")
            decision = PolicyEngine().authorize_tool(
                user_goal=plan.user_goal,
                tool_name=step.tool_name,
                read_only=metadata.read_only,
                server_mode=self.server_mode,
            )
            if not decision.allowed:
                raise ValueError(decision.reason_code)
        _, _, required_tool = self.route(original_goal)
        if required_tool not in {step.tool_name for step in plan.steps}:
            raise ValueError("REQUIRED_EVIDENCE_TOOL_MISSING")

    @staticmethod
    def route(goal: str) -> tuple[Intent, Complexity, str]:
        lower = goal.lower()
        if any(term in lower for term in ("清理", "垃圾", "旧日志", "缓存", "cleanup")):
            return Intent.CLEANUP, Complexity.COMPLEX, "large_file_scan"
        if any(term in lower for term in ("磁盘", "disk", "空间")):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "disk_usage_scan"
        if any(term in lower for term in ("进程", "process", "cpu", "僵尸")):
            return Intent.DIAGNOSIS, Complexity.MEDIUM, "process_list"
        if any(term in lower for term in ("端口", "port", "socket")):
            return Intent.QUERY, Complexity.SIMPLE, "network_socket_list"
        return Intent.QUERY, Complexity.SIMPLE, "system_snapshot"

    def _rule_fallback(self, goal: str) -> ActionPlan:
        intent, complexity, tool = self.route(goal)
        return ActionPlan(
            plan_id=str(uuid.uuid4()),
            user_goal=goal,
            intent=intent,
            complexity=complexity,
            summary="规则降级生成的只读诊断计划",
            steps=[PlanStep(sequence=1, tool_name=tool, purpose="采集只读系统证据")],
            expected_evidence=[tool],
            risk_level="L2" if intent == Intent.CLEANUP else "L1",
            requires_approval=False,
            verification="校验工具返回结构和证据来源",
            rollback="只读计划不适用回滚",
            public_reason="LLM 当前不可用，已使用确定性只读路由采集系统证据。",
        )

    @staticmethod
    def _forbidden(goal: str) -> ActionPlan:
        return ActionPlan(
            plan_id=str(uuid.uuid4()),
            user_goal=goal,
            intent=Intent.FORBIDDEN,
            complexity=Complexity.SIMPLE,
            summary="请求已被安全规则拒绝",
            steps=[],
            expected_evidence=[],
            risk_level="L4",
            requires_approval=False,
            verification="未调用系统工具",
            rollback="不适用",
            public_reason="请求命中禁止规则，系统未调用任何工具。",
        )
