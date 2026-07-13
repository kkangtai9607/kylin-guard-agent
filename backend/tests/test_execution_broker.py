from __future__ import annotations

import json
import sqlite3
from hashlib import sha256
from pathlib import Path

import pytest

from backend.app.executor.broker import (
    BrokerResponse,
    BrokerSystemctlRunner,
    LocalExecutionBroker,
    _authorize_and_consume,
    _parse_request,
    _parse_response,
)
from backend.app.executor.systemd import CommandOutcome


def test_broker_protocol_rejects_extra_fields_and_invalid_response() -> None:
    with pytest.raises(ValueError, match="BROKER_SCHEMA_INVALID"):
        _parse_request(b'{"action":"service_restart","service":"nginx","version":1,"extra":1}')
    with pytest.raises(ValueError, match="BROKER_RESPONSE_INVALID"):
        _parse_response(b'{"returncode":"0","stdout":"","stderr":""}')


def test_broker_systemctl_runner_uses_broker_only_for_fixed_restart(tmp_path: Path) -> None:
    systemctl = tmp_path / "systemctl"
    systemctl.write_text("placeholder", encoding="utf-8")

    class FakeBroker(LocalExecutionBroker):
        def __init__(self) -> None:
            self.called: str | None = None

        def restart_service(
            self, *, service: str, user_id: str, task_id: str, approval_token: str
        ) -> CommandOutcome:
            del user_id, task_id, approval_token
            self.called = service
            return CommandOutcome(0, "", "")

    broker = FakeBroker()
    runner = BrokerSystemctlRunner(systemctl, broker)
    credential = "test-approval-token"
    outcome = runner.restart_with_approval(
        service="nginx", user_id="user", task_id="task", approval_token=credential
    )
    assert outcome.returncode == 0
    assert broker.called == "nginx"
    with pytest.raises(ValueError, match="BROKER_ACTION_NOT_ALLOWED"):
        runner.restart_with_approval(
            service="sshd", user_id="user", task_id="task", approval_token=credential
        )


def test_broker_response_shape_is_stable() -> None:
    raw = json.dumps(BrokerResponse(0, "ok", "").__dict__).encode()
    assert _parse_response(raw) == BrokerResponse(0, "ok", "")


def test_broker_consumes_only_matching_persisted_approval(tmp_path: Path) -> None:
    database_path = tmp_path / "guard.db"
    approval_credential = "t" * 64
    arguments_hash = sha256(b'{"service":"nginx"}').hexdigest()
    with sqlite3.connect(database_path) as db:
        db.execute(
            "CREATE TABLE approvals (id TEXT, token_hash TEXT, status TEXT, requester_id TEXT, "
            "task_id TEXT, tool_name TEXT, arguments_hash TEXT, expires_at TEXT)"
        )
        db.execute(
            "INSERT INTO approvals VALUES (?, ?, 'APPROVED', 'user', 'task', 'service_restart', ?, ?) ",
            (
                "approval",
                sha256(approval_credential.encode()).hexdigest(),
                arguments_hash,
                "2099-01-01 00:00:00",
            ),
        )
    request = {
        "version": 1,
        "action": "service_restart",
        "service": "nginx",
        "user_id": "user",
        "task_id": "task",
        "approval_token": approval_credential,
    }
    assert _authorize_and_consume(database_path, request) == ("service_restart", "nginx")
    with pytest.raises(ValueError, match="BROKER_APPROVAL_DENIED"):
        _authorize_and_consume(database_path, request)
