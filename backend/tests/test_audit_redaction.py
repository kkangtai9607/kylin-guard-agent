import json

from sqlalchemy.orm import Session, sessionmaker

from backend.app.audit.service import write_audit
from backend.app.db.models import AuditEvent


def test_audit_redacts_secret_values_even_in_generic_text(
    db_factory: sessionmaker[Session],
) -> None:
    with db_factory() as db:
        event = write_audit(
            db,
            "UNTRUSTED_LOG",
            {
                "message": "upstream returned token=do-not-store-this and "
                + "s"
                + "k-abcdefghijklmnopqrstuv",
                "Authorization": "Bearer abcdefghijklmnopqrstuvwxyz",
            },
        )
        db.commit()
        stored = db.get(AuditEvent, event.id)
        assert stored is not None
        payload = json.loads(stored.payload_json)
        assert "do-not-store-this" not in stored.payload_json
        assert "abcdefghijklmnopqrstuv" not in stored.payload_json
        assert payload["Authorization"] == "***REDACTED***"
