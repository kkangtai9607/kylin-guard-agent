from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.app.agent.cleanup import CleanupAnalysisService
from backend.app.agent.normalization import EvidenceNormalizer
from backend.app.agent.planning import ActionPlan, Intent, Planner
from backend.app.agent.rca import RCAEngine
from backend.app.agent.runners import PlanAndExecuteRunner, ReActRunner, ResponseComposer
from backend.app.guardrails.untrusted import sanitize_text
from backend.app.mcp_client.client import KylinGuardMCPClient


class AgentOrchestrator:
    def __init__(
        self,
        planner: Planner,
        mcp: KylinGuardMCPClient,
        knowledge_search: Callable[[str], list[Any]] | None = None,
    ) -> None:
        self.planner = planner
        self.mcp = mcp
        self.knowledge_search = knowledge_search

    def run(self, goal: str) -> dict[str, Any]:
        plan = self.planner.plan(goal)
        if plan.intent == Intent.FORBIDDEN:
            return {
                "plan": plan.model_dump(mode="json"),
                "evidence": [],
                "normalized_evidence": [],
                "root_causes": [],
                "knowledge_hits": [],
                "cleanup_analysis": [],
                "status": "BLOCKED",
                "decision_chain": [
                    {"stage": "用户目标", "reason_code": "GOAL_RECEIVED", "summary": goal},
                    {
                        "stage": "输入护栏",
                        "reason_code": "FORBIDDEN_INPUT",
                        "summary": "请求被确定性安全规则阻断，未调用系统工具。",
                    },
                ],
            }
        evidence, status = PlanAndExecuteRunner(ReActRunner(self.mcp)).run(plan)
        composed = ResponseComposer().compose(plan, evidence, status)
        normalized = EvidenceNormalizer().normalize(evidence)
        root_causes = RCAEngine().analyze(normalized)
        knowledge_hits: list[dict[str, Any]] = []
        if self.knowledge_search is not None:
            try:
                hits = self.knowledge_search(goal)
                knowledge_hits = [
                    {
                        "document_id": item.document_id,
                        "title": item.title,
                        "snippet": sanitize_text(item.snippet, max_text_bytes=4096),
                        "review_status": item.review_status,
                        "trust_label": "UNTRUSTED_DATA",
                    }
                    for item in hits[:5]
                    if item.review_status == "APPROVED"
                ]
            except (OSError, ValueError):
                knowledge_hits = []
        cleanup_analysis: list[dict[str, Any]] = []
        if plan.intent == Intent.CLEANUP and evidence:
            decisions = CleanupAnalysisService(self.mcp).analyze_large_file_result(
                evidence[0].payload
            )
            cleanup_analysis = [item.model_dump(mode="json") for item in decisions]
        return {
            "plan": plan.model_dump(mode="json"),
            **composed,
            "normalized_evidence": [item.model_dump(mode="json") for item in normalized],
            "root_causes": [item.model_dump(mode="json") for item in root_causes],
            "knowledge_hits": knowledge_hits,
            "cleanup_analysis": cleanup_analysis,
            "decision_chain": self._decision_chain(
                plan=plan,
                status=status,
                evidence_count=len(normalized),
                root_cause_count=len(root_causes),
                knowledge_count=len(knowledge_hits),
            ),
        }

    @staticmethod
    def _decision_chain(
        *,
        plan: ActionPlan,
        status: str,
        evidence_count: int,
        root_cause_count: int,
        knowledge_count: int,
    ) -> list[dict[str, object]]:
        return [
            {"stage": "用户目标", "reason_code": "GOAL_ACCEPTED", "summary": plan.user_goal},
            {
                "stage": "意图分类",
                "reason_code": f"INTENT_{plan.intent.value}",
                "summary": f"复杂度 {plan.complexity.value}",
            },
            {
                "stage": "结构化计划",
                "reason_code": "PLAN_SCHEMA_VALID",
                "summary": f"{len(plan.steps)} 个白名单步骤，风险 {plan.risk_level}",
            },
            {
                "stage": "确定性护栏",
                "reason_code": "POLICY_ALLOWED",
                "summary": "工具、模式、参数和风险下限校验通过",
            },
            {
                "stage": "证据与知识",
                "reason_code": "UNTRUSTED_DATA_ISOLATED",
                "summary": f"{evidence_count} 条证据，{knowledge_count} 条已审核知识命中",
            },
            {
                "stage": "根因分析",
                "reason_code": "RCA_SCORED",
                "summary": f"生成 {root_cause_count} 个可解释候选",
            },
            {"stage": "任务结果", "reason_code": status, "summary": "公开决策摘要"},
        ]
