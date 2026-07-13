from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from backend.app.core.config import get_config


def login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def test_approval_rbac_and_decision(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("KYLIN_GUARD_MODE", "CONTROLLED_EXECUTION")
    monkeypatch.setenv("APPROVAL_HMAC_KEY", "x" * 32)
    get_config.cache_clear()
    try:
        operator = login(client, "operator")
        approver = login(client, "approver")
        task = client.post(
            "/api/v1/tasks",
            headers=operator,
            json={"goal": "restart nginx", "requested_mode": "CONTROLLED_EXECUTION"},
        )
        assert task.status_code == 201
        approval = client.post(
            f"/api/v1/tasks/{task.json()['data']['id']}/approvals",
            headers=operator,
            json={"tool_name": "service_restart", "arguments": {"service": "nginx"}},
        )
        assert approval.status_code == 201
        approval_id = approval.json()["data"]["id"]
        assert client.get("/api/v1/approvals", headers=operator).status_code == 403
        assert client.get(f"/api/v1/approvals/{approval_id}", headers=approver).status_code == 200
        approved = client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=approver,
            json={"reason": "verified change"},
        )
        assert approved.status_code == 200
        assert approved.json()["data"]["status"] == "APPROVED"
        assert "approval_token" not in approved.json()["data"]
        assert client.post(f"/api/v1/approvals/{approval_id}/claim", headers=approver).status_code == 403
        claimed = client.post(f"/api/v1/approvals/{approval_id}/claim", headers=operator)
        assert claimed.status_code == 200
        assert "approval_token" in claimed.json()["data"]
        repeated = client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=approver,
            json={"reason": "repeat"},
        )
        assert repeated.status_code == 409
    finally:
        get_config.cache_clear()
