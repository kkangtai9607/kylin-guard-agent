from sqlalchemy.orm import Session, sessionmaker

from backend.app.audit.service import verify_chain, write_audit
from backend.app.core.config_drift import detect_drift
from backend.app.core.trends import analyze_trend
from backend.app.db.models import AuditEvent


def test_trend_is_repeatable_and_explains_window() -> None:
    first = analyze_trend([10, 11, 12, 30])
    second = analyze_trend([10, 11, 12, 30])
    assert first == second
    assert first.window == 4 and first.anomalous
    assert "EWMA" in first.basis


def test_config_drift_redacts_sensitive_lines() -> None:
    result = detect_drift("port=80\npassword=old", "port=81\npassword=new")
    assert result.changed
    assert any("REDACTED" in line for line in result.diff_summary)
    assert all("old" not in line and "new" not in line for line in result.diff_summary)


def test_audit_hash_chain_detects_tamper(db_factory: sessionmaker[Session]) -> None:
    with db_factory() as db:
        assert isinstance(db, Session)
        write_audit(db, "FIRST", {"safe": "one"})
        write_audit(db, "SECOND", {"token": "must-redact"})
        db.commit()
        assert verify_chain(db) == (True, None)
        event = db.query(AuditEvent).filter(AuditEvent.event_type == "FIRST").one()
        event.payload_json = "tampered"
        db.commit()
        valid, broken_id = verify_chain(db)
        assert not valid and broken_id == event.id
