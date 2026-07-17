from fastapi.testclient import TestClient

from backend.app.api.router import _task_scoped_cleanup_candidate_id


def test_cleanup_candidates_endpoint_requires_auth_and_starts_empty(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    assert client.get("/api/v1/cleanup/candidates").status_code == 401
    response = client.get("/api/v1/cleanup/candidates", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_cleanup_candidate_id_is_scoped_to_current_task() -> None:
    base = "cleanup-1234567890abcdef12345678"
    task_id = "abcdef12-3456-7890-abcd-ef1234567890"

    scoped = _task_scoped_cleanup_candidate_id(base, task_id)

    assert scoped == "cleanup-1234567890abcdef12345678-abcdef12-345"
    assert _task_scoped_cleanup_candidate_id(scoped, task_id) == scoped
