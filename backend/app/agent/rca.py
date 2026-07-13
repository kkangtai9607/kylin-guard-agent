from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from backend.app.agent.evidence import Evidence


class RootCauseCandidate(BaseModel):
    title: str
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str]
    reason_summary: str
    recommended_actions: list[str]


RULES: dict[str, tuple[set[str], float, str]] = {
    "disk_pressure": ({"disk", "space", "large_file"}, 0.9, "检查并归档安全候选日志"),
    "high_cpu": ({"cpu", "load", "process"}, 0.85, "检查高 CPU 进程及关联日志"),
    "zombie_process": ({"zombie", "process"}, 0.8, "检查父进程并评估受控处置"),
    "service_failure": ({"service", "failed", "journal"}, 0.85, "核对配置和服务日志"),
    "config_drift": ({"config", "drift"}, 0.8, "比较已审核基线并生成修复建议"),
}


class RCAEngine:
    def analyze(self, evidence: list[Evidence]) -> list[RootCauseCandidate]:
        grouped: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence:
            text = " ".join([item.title, item.source, *item.tags]).lower()
            for rule, (keywords, _, _) in RULES.items():
                if keywords.intersection(text.split()):
                    grouped[rule].append(item)
        candidates: list[RootCauseCandidate] = []
        for rule, items in grouped.items():
            _, weight, action = RULES[rule]
            anomaly = sum(item.anomaly_score for item in items) / len(items)
            temporal = sum(item.temporal_score for item in items) / len(items)
            source_bonus = min(len({item.evidence_type for item in items}) * 0.08, 0.24)
            conflict_penalty = sum(0.1 for item in items if "conflict" in item.tags)
            confidence = max(
                0.0,
                min(
                    1.0,
                    weight * (0.55 * anomaly + 0.25 * temporal + 0.2)
                    + source_bonus
                    - conflict_penalty,
                ),
            )
            candidates.append(
                RootCauseCandidate(
                    title=rule,
                    confidence=round(confidence, 3),
                    evidence_ids=[item.evidence_id for item in items],
                    reason_summary=f"{len(items)} 条可追溯证据命中规则 {rule}",
                    recommended_actions=[action],
                )
            )
        return sorted(candidates, key=lambda item: item.confidence, reverse=True)[:3]
