from fastapi.testclient import TestClient


def test_controlled_capabilities_are_public_metadata_but_authenticated(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert client.get("/api/v1/controlled/capabilities").status_code == 401
    response = client.get("/api/v1/controlled/capabilities", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mode"] == "CONTROLLED_EXECUTION"
    assert data["enabled"] is True
    assert "service_restart" in data["tools"]
    assert data["production_available_tools"] == []
    assert data["execution_broker"]["available"] is False
    assert data["managed_configs"][0]["target_id"] == "nginx-main"
    assert "validator_path" not in str(data)


def test_execution_history_requires_authorization(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert client.get("/api/v1/executions").status_code == 401
    response = client.get("/api/v1/executions", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json()["data"], list)


def test_service_status_self_test_uses_only_default_allowlisted_service(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post("/api/v1/mcp/tools/service_status/test", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["tool_name"] == "service_status"


def test_mcp_tool_self_test_returns_failed_result_instead_of_http_error(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/mcp/tools/unknown_tool/test",
        headers=auth_headers,
        json={"arguments": {}},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["tool_name"] == "unknown_tool"
    assert data["status"] == "FAILED"
    assert data["error_code"] == "TOOL_NOT_REGISTERED"
