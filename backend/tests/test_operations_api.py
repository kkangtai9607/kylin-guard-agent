import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.inspection_service import _derive_incidents
from backend.app.core.snapshot_scheduler import PeriodicSnapshotService
from backend.app.db.models import Incident, SystemSnapshot


def test_real_operational_endpoints(client: TestClient, auth_headers: dict[str, str]) -> None:
    overview = client.get("/api/v1/system/overview", headers=auth_headers)
    assert overview.status_code == 200
    inspection = client.post("/api/v1/inspections/run", headers=auth_headers)
    assert inspection.status_code == 201
    assert client.get("/api/v1/inspections", headers=auth_headers).json()["data"]
    assert client.get("/api/v1/incidents", headers=auth_headers).status_code == 200

    path_ref = f"config-{uuid.uuid4()}"
    baseline = client.post(
        "/api/v1/config-drift/baselines",
        headers=auth_headers,
        json={"path_ref": path_ref, "content": "port=80\npassword=secret"},
    )
    assert baseline.status_code == 201
    drift = client.post(
        "/api/v1/config-drift/check",
        headers=auth_headers,
        json={"path_ref": path_ref, "current_content": "port=81\npassword=changed"},
    )
    assert drift.status_code == 200
    assert drift.json()["data"]["changed"] is True
    assert "secret" not in str(drift.json()).lower()

    settings = client.put(
        "/api/v1/settings",
        headers=auth_headers,
        json={"snapshot_interval_seconds": 120, "retention_days": 14},
    )
    assert settings.status_code == 200
    loaded = client.get("/api/v1/settings", headers=auth_headers)
    assert loaded.json()["data"]["snapshot_interval_seconds"] == 120


def test_periodic_snapshot_service_runs_and_stops() -> None:
    async def scenario() -> int:
        count = 0

        async def capture() -> None:
            nonlocal count
            count += 1

        service = PeriodicSnapshotService(0.01, capture)
        service.start()
        await asyncio.sleep(0.035)
        await service.stop()
        return count

    assert asyncio.run(scenario()) >= 2


def test_inspection_derives_and_deduplicates_incidents(
    db_factory: sessionmaker[Session],
) -> None:
    with db_factory() as db:
        snapshot = SystemSnapshot(payload_json="{}", is_demo=True)
        db.add(snapshot)
        db.flush()
        created = _derive_incidents(
            db,
            snapshot,
            {"disk": {"total": 100, "used": 91}},
            {"checks": [{"id": "policy", "status": "FAIL"}]},
        )
        assert {item.severity for item in created} == {"CRITICAL", "WARNING"}
        assert _derive_incidents(
            db,
            snapshot,
            {"disk": {"total": 100, "used": 91}},
            {"checks": [{"id": "policy", "status": "FAIL"}]},
        ) == []
        assert db.query(Incident).count() == 2


def test_incident_status_can_be_updated(
    client: TestClient,
    auth_headers: dict[str, str],
    db_factory: sessionmaker[Session],
) -> None:
    with db_factory() as db:
        incident = Incident(severity="WARNING", summary="test incident")
        db.add(incident)
        db.commit()
        incident_id = incident.id
    response = client.put(
        f"/api/v1/incidents/{incident_id}",
        headers=auth_headers,
        json={"status": "ACKNOWLEDGED"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ACKNOWLEDGED"
