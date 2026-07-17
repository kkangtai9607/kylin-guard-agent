from fastapi.testclient import TestClient


def test_health_is_public_and_operations_mode(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["meta"]["mode"] == "CONTROLLED_EXECUTION"


def test_login_and_protected_endpoint(client: TestClient, auth_headers: dict[str, str]) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "admin"


def test_logout_revokes_session(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "StrongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {response.json()['data']['access_token']}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_task_create_and_transition(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"goal": "检查系统状态", "requested_mode": "CONTROLLED_EXECUTION"},
    )
    assert created.status_code == 201
    task_id = created.json()["data"]["id"]
    changed = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        headers=auth_headers,
        json={"target_state": "INPUT_GUARD", "reason_code": "INPUT_ACCEPTED"},
    )
    assert changed.status_code == 200
    assert changed.json()["data"]["state"] == "INPUT_GUARD"


def test_task_list_and_cancel(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post("/api/v1/tasks", headers=auth_headers, json={"goal": "可取消任务"})
    task_id = created.json()["data"]["id"]
    assert any(
        item["id"] == task_id
        for item in client.get("/api/v1/tasks", headers=auth_headers).json()["data"]
    )
    cancelled = client.post(f"/api/v1/tasks/{task_id}/cancel", headers=auth_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["state"] == "CANCELLED"


def test_illegal_transition_is_rejected_and_audit_is_queryable(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post("/api/v1/tasks", headers=auth_headers, json={"goal": "检查服务"})
    task_id = created.json()["data"]["id"]
    rejected = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        headers=auth_headers,
        json={"target_state": "EXECUTING", "reason_code": "SKIP"},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "INVALID_STATE_TRANSITION"
    audit = client.get("/api/v1/audit/events", headers=auth_headers)
    assert audit.status_code == 200
    assert any(item["event_type"] == "TASK_CREATED" for item in audit.json()["data"])


def test_unknown_task_and_extra_input_do_not_leak_details(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    missing = client.get("/api/v1/tasks/missing", headers=auth_headers)
    assert missing.status_code == 404
    invalid = client.post(
        "/api/v1/tasks",
        headers=auth_headers,
        json={"goal": "test", "command": "whoami"},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["message"] == "request validation failed"


def test_rule_fallback_agent_run_and_events(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post("/api/v1/tasks", headers=auth_headers, json={"goal": "检查系统状态"})
    task_id = created.json()["data"]["id"]
    run = client.post(f"/api/v1/tasks/{task_id}/run", headers=auth_headers)
    assert run.status_code == 200
    assert run.json()["data"]["status"] == "SUCCEEDED"
    events = client.get(f"/api/v1/tasks/{task_id}/events", headers=auth_headers)
    assert events.status_code == 200
    assert any(item["event_type"] == "AGENT_RUN_COMPLETED" for item in events.json()["data"])
    stream = client.get(f"/api/v1/tasks/{task_id}/stream", headers=auth_headers)
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert "event: task" in stream.text
