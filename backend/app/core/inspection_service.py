from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.audit.service import write_audit
from backend.app.db.models import Incident, SystemSnapshot
from backend.app.mcp_client.client import KylinGuardMCPClient


@dataclass(frozen=True)
class InspectionResult:
    snapshot: SystemSnapshot
    baseline: dict[str, object]
    incidents: tuple[Incident, ...]


def capture_inspection(db: Session, actor_id: str | None = None) -> InspectionResult:
    """Capture one inspection and derive incidents using deterministic thresholds."""
    client = KylinGuardMCPClient()
    snapshot_result = client.call_tool("system_snapshot")
    baseline_result = client.call_tool("security_baseline_scan")
    snapshot = SystemSnapshot(
        payload_json=json.dumps(snapshot_result.model_dump(mode="json"), ensure_ascii=False),
        is_demo=snapshot_result.is_demo,
    )
    db.add(snapshot)
    db.flush()

    incidents = tuple(_derive_incidents(db, snapshot, snapshot_result.data, baseline_result.data))
    write_audit(
        db,
        "INSPECTION_COMPLETED",
        {
            "snapshot_id": snapshot.id,
            "incident_ids": [item.id for item in incidents],
            "baseline": baseline_result.model_dump(mode="json"),
        },
        actor_id=actor_id,
    )
    db.commit()
    return InspectionResult(
        snapshot=snapshot,
        baseline=baseline_result.model_dump(mode="json"),
        incidents=incidents,
    )


def _derive_incidents(
    db: Session,
    snapshot: SystemSnapshot,
    snapshot_data: dict[str, object],
    baseline_data: dict[str, object],
) -> list[Incident]:
    findings: list[tuple[str, str]] = []
    disk = snapshot_data.get("disk")
    if isinstance(disk, dict):
        total = disk.get("total")
        used = disk.get("used")
        if isinstance(total, (int, float)) and isinstance(used, (int, float)) and total > 0:
            ratio = used / total
            if ratio >= 0.9:
                findings.append(("CRITICAL", f"磁盘使用率达到 {ratio:.1%}"))
            elif ratio >= 0.8:
                findings.append(("WARNING", f"磁盘使用率达到 {ratio:.1%}"))

    filesystems = snapshot_data.get("filesystems")
    if isinstance(filesystems, list):
        for item in filesystems[:20]:
            if not isinstance(item, dict):
                continue
            total = item.get("total")
            used = item.get("used")
            path = str(item.get("path", "unknown"))
            if isinstance(total, (int, float)) and isinstance(used, (int, float)) and total > 0:
                ratio = used / total
                if ratio >= 0.9:
                    findings.append(("CRITICAL", f"{path} 磁盘使用率达到 {ratio:.1%}"))
                elif ratio >= 0.8:
                    findings.append(("WARNING", f"{path} 磁盘使用率达到 {ratio:.1%}"))

    checks = baseline_data.get("checks")
    if isinstance(checks, list):
        for item in checks[:50]:
            if not isinstance(item, dict) or item.get("status") in {"PASS", "SKIPPED"}:
                continue
            check_id = str(item.get("id", "unknown"))
            value = str(item.get("value", ""))[:200]
            severity = "CRITICAL" if check_id.startswith("service_") else "WARNING"
            findings.append((severity, f"安全巡检异常：{check_id}={value}"))

    created: list[Incident] = []
    for severity, summary in findings:
        duplicate = db.scalar(
            select(Incident).where(Incident.status == "OPEN", Incident.summary == summary)
        )
        if duplicate is not None:
            continue
        incident = Incident(
            snapshot_id=snapshot.id,
            severity=severity,
            status="OPEN",
            summary=summary,
        )
        db.add(incident)
        db.flush()
        created.append(incident)
    return created
