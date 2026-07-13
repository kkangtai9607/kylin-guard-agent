from backend.app.audit.service import redact
from backend.app.auth.security import hash_password, verify_password


def test_password_hash_is_salted_and_verifiable() -> None:
    first = hash_password("StrongPassword123!")
    second = hash_password("StrongPassword123!")
    assert first != second
    assert "StrongPassword123!" not in first
    assert verify_password("StrongPassword123!", first)
    assert not verify_password("wrong-password", first)


def test_audit_redaction_is_recursive() -> None:
    value = {"api_key": "secret", "nested": {"Authorization": "Bearer value"}, "safe": "ok"}
    assert redact(value) == {
        "api_key": "***REDACTED***",
        "nested": {"Authorization": "***REDACTED***"},
        "safe": "ok",
    }
