from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.models import (
    EvidenceRecordModel,
    GuardDecisionRecord,
    ToolCallRecord,
)


def test_agent_run_persists_structured_public_trace(
    client: TestClient,
    auth_headers: dict[str, str],
    db_factory: sessionmaker[Session],
) -> None:
    created = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"goal": "检查系统状态", "requested_mode": "READ_ONLY"},
    )
    assert created.status_code == 201
    task_id = created.json()["data"]["id"]
    run = client.post(f"/api/v1/tasks/{task_id}/run", headers=auth_headers)
    assert run.status_code == 200
    assert run.json()["data"]["decision_chain"]
    with db_factory() as db:
        tool_count = db.scalar(
            select(func.count()).select_from(ToolCallRecord).where(ToolCallRecord.task_id == task_id)
        )
        evidence_count = db.scalar(
            select(func.count())
            .select_from(EvidenceRecordModel)
            .where(EvidenceRecordModel.task_id == task_id)
        )
        guard_count = db.scalar(
            select(func.count())
            .select_from(GuardDecisionRecord)
            .where(GuardDecisionRecord.task_id == task_id)
        )
        assert tool_count and tool_count >= 1
        assert evidence_count and evidence_count >= 1
        assert guard_count and guard_count >= 5
        decisions = db.scalars(
            select(GuardDecisionRecord).where(GuardDecisionRecord.task_id == task_id)
        ).all()
        assert all("thought" not in item.public_summary.lower() for item in decisions)
