from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from backend.app.core.config import get_config
from backend.tests.test_approvals_api import login


def test_demo_approval_execution_and_replay_block(
    client: TestClient, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("KYLIN_GUARD_MODE", "DEMO")
    monkeypatch.setenv("APPROVAL_HMAC_KEY", "d" * 32)
    get_config.cache_clear()
    try:
        operator = login(client, "operator")
        approver = login(client, "approver")
        reset = client.post("/api/v1/demo/reset", headers=operator)
        assert reset.status_code == 201
        candidate_id = reset.json()["data"]["log_candidate_id"]
        arguments = {"candidate_id": candidate_id}
        preview = client.post(
            "/api/v1/executions/dry-run",
            headers=operator,
            json={"tool_name": "safe_log_cleanup", "arguments": arguments},
        )
        assert preview.status_code == 200
        task = client.post(
            "/api/v1/tasks",
            headers=operator,
            json={"goal": "清理已识别的 DEMO 旧日志", "requested_mode": "DEMO"},
        )
        task_id = task.json()["data"]["id"]
        approval = client.post(
            f"/api/v1/tasks/{task_id}/approvals",
            headers=operator,
            json={"tool_name": "safe_log_cleanup", "arguments": arguments},
        )
        approval_id = approval.json()["data"]["id"]
        approved = client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=approver,
            json={"reason": "DEMO candidate and impact verified"},
        )
        assert "approval_token" not in approved.json()["data"]
        token = client.post(
            f"/api/v1/approvals/{approval_id}/claim", headers=operator
        ).json()["data"]["approval_token"]
        body = {
            "task_id": task_id,
            "tool_name": "safe_log_cleanup",
            "arguments": arguments,
            "approval_token": token,
        }
        executed = client.post("/api/v1/executions/run", headers=operator, json=body)
        assert executed.status_code == 200
        assert executed.json()["data"]["status"] == "SUCCEEDED"
        repeated = client.post("/api/v1/executions/run", headers=operator, json=body)
        assert repeated.status_code == 403
    finally:
        get_config.cache_clear()
