import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.agent.evidence import Evidence, EvidenceType
from backend.app.agent.rca import RCAEngine
from backend.app.knowledge.service import FTSKnowledgeBase


def test_rca_confidence_is_computed_and_traceable() -> None:
    evidence = [
        Evidence(
            evidence_id="e1",
            evidence_type=EvidenceType.METRIC,
            source="disk",
            title="disk space",
            value=95,
            anomaly_score=0.95,
            temporal_score=0.8,
            tags=["disk", "space"],
        ),
        Evidence(
            evidence_id="e2",
            evidence_type=EvidenceType.LOG,
            source="large_file",
            title="large file",
            value="app.log",
            anomaly_score=0.8,
            temporal_score=0.7,
            tags=["large_file", "disk"],
        ),
    ]
    candidates = RCAEngine().analyze(evidence)
    assert candidates[0].title == "disk_pressure"
    assert candidates[0].confidence > 0.7
    assert candidates[0].evidence_ids == ["e1", "e2"]


def test_rca_returns_no_conclusion_without_evidence() -> None:
    assert RCAEngine().analyze([]) == []


def test_conflicting_evidence_lowers_confidence() -> None:
    normal = Evidence(
        evidence_id="e1",
        evidence_type=EvidenceType.METRIC,
        source="cpu",
        title="cpu load",
        value=90,
        anomaly_score=0.9,
        temporal_score=0.9,
        tags=["cpu"],
    )
    conflict = normal.model_copy(update={"evidence_id": "e2", "tags": ["cpu", "conflict"]})
    assert (
        RCAEngine().analyze([normal])[0].confidence > RCAEngine().analyze([conflict])[0].confidence
    )


def test_fts5_search_and_review_status(tmp_path: Path) -> None:
    knowledge = FTSKnowledgeBase(tmp_path / "knowledge.db")
    knowledge.initialize()
    knowledge.add("d1", "磁盘空间处理", "磁盘 日志 归档 清理", "APPROVED")
    knowledge.add("d2", "未审核案例", "磁盘 删除", "PENDING")
    hits = knowledge.search("磁盘")
    assert len(hits) == 2
    assert all(hit.trust_label == "UNTRUSTED_DATA" for hit in hits)
    assert {hit.review_status for hit in hits} == {"APPROVED", "PENDING"}


def test_rca_and_knowledge_api(client: TestClient, auth_headers: dict[str, str]) -> None:
    rca = client.post(
        "/api/v1/rca/analyze",
        headers=auth_headers,
        json=[
            {
                "evidence_id": "api-e1",
                "evidence_type": "METRIC",
                "source": "disk",
                "title": "disk space",
                "value": 95,
                "anomaly_score": 0.95,
                "temporal_score": 0.8,
                "tags": ["disk", "space"],
            }
        ],
    )
    assert rca.status_code == 200
    assert rca.json()["data"]["candidates"][0]["evidence_ids"] == ["api-e1"]
    document_id = str(uuid.uuid4())
    created = client.post(
        "/api/v1/knowledge",
        headers=auth_headers,
        json={
            "document_id": document_id,
            "title": "UniqueDiskGuide",
            "content": "uniquediskterm archive",
            "review_status": "APPROVED",
        },
    )
    assert created.status_code == 201
    searched = client.get("/api/v1/knowledge?query=uniquediskterm", headers=auth_headers)
    assert searched.status_code == 200
    assert any(item["document_id"] == document_id for item in searched.json()["data"])
