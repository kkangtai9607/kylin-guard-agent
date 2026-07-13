from fastapi.testclient import TestClient


def test_cleanup_candidates_endpoint_requires_auth_and_starts_empty(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert client.get("/api/v1/cleanup/candidates").status_code == 401
    response = client.get("/api/v1/cleanup/candidates", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] == []
