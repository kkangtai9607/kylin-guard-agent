from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_config
from backend.app.db.models import Approval, ExecutionRecord, VerificationResultRecord


def login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def test_failed_attempt_consumes_approval_and_persists_failure(
    client: TestClient,
    db_factory: sessionmaker[Session],
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("KYLIN_GUARD_MODE", "DEMO")
    monkeypatch.setenv("APPROVAL_HMAC_KEY", "f" * 32)
    get_config.cache_clear()
    try:
        operator = login(client, "operator")
        approver = login(client, "approver")
        reset = client.post("/api/v1/demo/reset", headers=operator).json()["data"]
        task = client.post(
            "/api/v1/tasks",
            headers=operator,
            json={"goal": "清理演示旧日志", "requested_mode": "DEMO"},
        ).json()["data"]
        original_args = {"candidate_id": reset["log_candidate_id"]}
        approval = client.post(
            f"/api/v1/tasks/{task['id']}/approvals",
            headers=operator,
            json={"tool_name": "safe_log_cleanup", "arguments": original_args},
        ).json()["data"]
        approved = client.post(
            f"/api/v1/approvals/{approval['id']}/approve",
            headers=approver,
            json={"reason": "批准测试"},
        ).json()["data"]
        assert "approval_token" not in approved
        claimed = client.post(
            f"/api/v1/approvals/{approval['id']}/claim", headers=operator
        ).json()["data"]
        failed = client.post(
            "/api/v1/executions/run",
            headers=operator,
            json={
                "task_id": task["id"],
                "tool_name": "safe_log_cleanup",
                "arguments": {"candidate_id": "tampered-candidate"},
                "approval_token": claimed["approval_token"],
            },
        )
        assert failed.status_code == 422
        assert failed.json()["error"]["details"]["reason_code"]
        replay = client.post(
            "/api/v1/executions/run",
            headers=operator,
            json={
                "task_id": task["id"],
                "tool_name": "safe_log_cleanup",
                "arguments": original_args,
                "approval_token": claimed["approval_token"],
            },
        )
        assert replay.status_code == 403
        with db_factory() as db:
            stored_approval = db.get(Approval, approval["id"])
            assert stored_approval is not None and stored_approval.status == "CONSUMED"
            execution = db.scalar(
                select(ExecutionRecord).where(ExecutionRecord.approval_id == approval["id"])
            )
            assert execution is not None and execution.status == "FAILED"
            verification = db.scalar(
                select(VerificationResultRecord).where(
                    VerificationResultRecord.execution_id == execution.id
                )
            )
            assert verification is not None and verification.status == "FAILED"
    finally:
        get_config.cache_clear()
