from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.agent.planning import ActionPlan
from backend.app.guardrails.untrusted import contains_instruction_like_data, sanitize_untrusted
from backend.app.mcp_client.client import KylinGuardMCPClient


@dataclass(frozen=True)
class EvidenceRecord:
    tool_name: str
    payload: dict[str, Any]
    trust_label: str = "UNTRUSTED_DATA"
    injection_suspected: bool = False


class EvidenceManager:
    def collect(self, tool_name: str, payload: dict[str, Any]) -> EvidenceRecord:
        sanitized = sanitize_untrusted(payload)
        safe_payload = sanitized if isinstance(sanitized, dict) else {"value": sanitized}
        return EvidenceRecord(
            tool_name=tool_name,
            payload=safe_payload,
            injection_suspected=contains_instruction_like_data(safe_payload),
        )


class ReActRunner:
    """Bounded observe/select loop over a pre-validated registered Tool plan."""

    def __init__(self, mcp: KylinGuardMCPClient, max_steps: int = 5) -> None:
        if not 1 <= max_steps <= 10:
            raise ValueError("invalid ReAct step limit")
        self.mcp = mcp
        self.max_steps = max_steps
        self.evidence = EvidenceManager()

    def run(self, plan: ActionPlan) -> tuple[list[EvidenceRecord], str]:
        records: list[EvidenceRecord] = []
        for step in plan.steps[: self.max_steps]:
            result = self.mcp.call_tool(step.tool_name, step.arguments)
            records.append(self.evidence.collect(step.tool_name, result.model_dump(mode="json")))
            if result.status != "SUCCEEDED":
                return records, "FAILED"
        return records, "SUCCEEDED"


class PlanAndExecuteRunner:
    def __init__(self, react: ReActRunner) -> None:
        self.react = react

    def run(self, plan: ActionPlan) -> tuple[list[EvidenceRecord], str]:
        return self.react.run(plan)


class ResponseComposer:
    def compose(
        self, plan: ActionPlan, evidence: list[EvidenceRecord], status: str
    ) -> dict[str, Any]:
        return {
            "status": status,
            "summary": plan.summary,
            "public_reason": plan.public_reason,
            "evidence": [record.__dict__ for record in evidence],
        }
