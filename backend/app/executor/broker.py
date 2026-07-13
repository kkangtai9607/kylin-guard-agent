"""Fixed-action Linux broker with an independent persisted-approval check."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from backend.app.executor.systemd import CommandOutcome

_MAX_MESSAGE_BYTES = 8192
_PROTOCOL_VERSION = 1
_ACTION_RESTART = "service_restart"
_ACTION_ROLLBACK = "service_rollback"
_ALLOWED_SERVICE = "nginx"
_HELPER = "/usr/local/lib/kylin-guard/kylin_guard_privileged.py"
_SUDO = "/usr/bin/sudo"


@dataclass(frozen=True)
class BrokerResponse:
    returncode: int
    stdout: str
    stderr: str


class LocalExecutionBroker:
    """Unprivileged client. The persisted approval token remains mandatory."""

    def __init__(self, socket_path: Path, *, timeout_seconds: float = 35.0) -> None:
        self.socket_path = socket_path
        self.timeout_seconds = timeout_seconds

    def restart_service(
        self, *, service: str, user_id: str, task_id: str, approval_token: str
    ) -> CommandOutcome:
        return self._execute(_ACTION_RESTART, service, user_id, task_id, approval_token, None)

    def rollback_service(
        self, *, service: str, user_id: str, task_id: str, change_id: str, approval_token: str
    ) -> CommandOutcome:
        return self._execute(_ACTION_ROLLBACK, service, user_id, task_id, approval_token, change_id)

    def is_available(self) -> bool:
        try:
            return self.socket_path.is_socket()
        except OSError:
            return False

    def _execute(
        self,
        action: str,
        service: str,
        user_id: str,
        task_id: str,
        approval_token: str,
        change_id: str | None,
    ) -> CommandOutcome:
        if service != _ALLOWED_SERVICE or action not in {_ACTION_RESTART, _ACTION_ROLLBACK}:
            raise ValueError("BROKER_ACTION_NOT_ALLOWED")
        request: dict[str, object] = {
            "version": _PROTOCOL_VERSION,
            "action": action,
            "service": service,
            "user_id": user_id,
            "task_id": task_id,
            "approval_token": approval_token,
        }
        if change_id is not None:
            request["change_id"] = change_id
        response = self._request(request)
        return CommandOutcome(response.returncode, response.stdout, response.stderr)

    def _request(self, request: dict[str, object]) -> BrokerResponse:
        payload = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(payload) > _MAX_MESSAGE_BYTES:
            raise ValueError("BROKER_REQUEST_TOO_LARGE")
        try:
            with socket.socket(_unix_socket_family(), socket.SOCK_STREAM) as client:
                client.settimeout(self.timeout_seconds)
                client.connect(str(self.socket_path))
                client.sendall(payload + b"\n")
                raw = _receive_line(client)
        except OSError as error:
            raise ValueError("EXECUTION_BROKER_UNAVAILABLE") from error
        return _parse_response(raw)


class BrokerSystemctlRunner:
    """Read-only state checks use systemctl; all mutation requires broker approval."""

    def __init__(self, executable: Path, broker: LocalExecutionBroker) -> None:
        self.executable = executable.resolve(strict=True)
        self.broker = broker
        if self.executable.name != "systemctl":
            raise ValueError("SYSTEMCTL_PATH_REJECTED")

    def restart_with_approval(
        self, *, service: str, user_id: str, task_id: str, approval_token: str
    ) -> CommandOutcome:
        if service != _ALLOWED_SERVICE:
            raise ValueError("BROKER_ACTION_NOT_ALLOWED")
        return self.broker.restart_service(
            service=service, user_id=user_id, task_id=task_id, approval_token=approval_token
        )

    def rollback_with_approval(
        self,
        *,
        service: str,
        user_id: str,
        task_id: str,
        change_id: str,
        approval_token: str,
    ) -> CommandOutcome:
        if service != _ALLOWED_SERVICE:
            raise ValueError("BROKER_ACTION_NOT_ALLOWED")
        return self.broker.rollback_service(
            service=service,
            user_id=user_id,
            task_id=task_id,
            change_id=change_id,
            approval_token=approval_token,
        )

    def run(self, argv: tuple[str, ...], *, timeout: int) -> CommandOutcome:
        if len(argv) != 3 or Path(argv[0]).resolve() != self.executable:
            raise ValueError("EXECUTABLE_NOT_ALLOWED")
        action, service = argv[1:]
        if action != "is-active" or service != _ALLOWED_SERVICE:
            raise ValueError("BROKER_ACTION_CONTEXT_REQUIRED")
        completed = subprocess.run(  # noqa: S603
            argv,
            capture_output=True,
            check=False,
            timeout=timeout,
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
            cwd="/",
        )
        return CommandOutcome(
            completed.returncode,
            completed.stdout[:65536].decode(errors="replace"),
            completed.stderr[:65536].decode(errors="replace"),
        )


def serve(socket_path: Path, allowed_client_user: str, database_path: Path) -> None:
    """Run as kylin-guard-exec; peer UID and one-time DB approval are checked."""
    try:
        import pwd
    except ImportError as error:  # pragma: no cover
        raise RuntimeError("BROKER_REQUIRES_LINUX") from error
    allowed_uid = pwd.getpwnam(allowed_client_user).pw_uid  # type: ignore[attr-defined]
    socket_path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    socket_path.unlink(missing_ok=True)
    old_umask = os.umask(0o007)
    try:
        with socket.socket(_unix_socket_family(), socket.SOCK_STREAM) as server:
            server.bind(str(socket_path))
            os.chmod(socket_path, 0o660)
            server.listen(16)
            while True:
                connection, _ = server.accept()
                with connection:
                    response = _handle_connection(connection, allowed_uid, database_path)
                    connection.sendall(_encode_response(response) + b"\n")
    finally:
        os.umask(old_umask)
        socket_path.unlink(missing_ok=True)


def _handle_connection(
    connection: socket.socket, allowed_uid: int, database_path: Path
) -> BrokerResponse:
    try:
        peer_option = getattr(socket, "SO_PEERCRED", None)
        if peer_option is None:
            return BrokerResponse(126, "", "BROKER_PEER_CREDENTIALS_UNAVAILABLE")
        credentials = connection.getsockopt(socket.SOL_SOCKET, peer_option, 12)
        if int.from_bytes(credentials[4:8], byteorder="little") != allowed_uid:
            return BrokerResponse(126, "", "BROKER_PEER_DENIED")
        request = _parse_request(_receive_line(connection))
        helper_args = _authorize_and_consume(database_path, request)
        completed = subprocess.run(  # noqa: S603
            (_SUDO, "-n", _HELPER, *helper_args),
            capture_output=True,
            check=False,
            timeout=35,
            env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},
            cwd="/",
        )
        return BrokerResponse(
            completed.returncode,
            completed.stdout[:65536].decode(errors="replace"),
            completed.stderr[:65536].decode(errors="replace"),
        )
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as error:
        return BrokerResponse(126, "", f"BROKER_DENIED:{type(error).__name__}")


def _authorize_and_consume(database_path: Path, request: dict[str, object]) -> tuple[str, str]:
    action = request["action"]
    service = request["service"]
    user_id = request["user_id"]
    task_id = request["task_id"]
    approval_token = request["approval_token"]
    if not all(isinstance(value, str) and value for value in (action, service, user_id, task_id, approval_token)):
        raise ValueError("BROKER_SCHEMA_INVALID")
    if service != _ALLOWED_SERVICE:
        raise ValueError("BROKER_SERVICE_NOT_ALLOWED")
    if action == _ACTION_RESTART:
        expected_tool, expected_arguments, helper_args = "service_restart", {"service": service}, (
            _ACTION_RESTART,
            service,
        )
    elif action == _ACTION_ROLLBACK:
        change_id = request.get("change_id")
        if not isinstance(change_id, str) or not change_id:
            raise ValueError("BROKER_SCHEMA_INVALID")
        expected_tool, expected_arguments, helper_args = "rollback_change", {"change_id": change_id}, (
            _ACTION_ROLLBACK,
            service,
        )
    else:
        raise ValueError("BROKER_ACTION_NOT_ALLOWED")
    arguments_hash = hashlib.sha256(
        json.dumps(expected_arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    token_hash = hashlib.sha256(cast(str, approval_token).encode()).hexdigest()
    with sqlite3.connect(database_path, timeout=5, isolation_level="IMMEDIATE") as database:
        row = database.execute(
            "SELECT id, expires_at FROM approvals WHERE token_hash = ? AND status = 'APPROVED' "
            "AND requester_id = ? AND task_id = ? AND tool_name = ? AND arguments_hash = ?",
            (token_hash, user_id, task_id, expected_tool, arguments_hash),
        ).fetchone()
        if row is None or _expired(row[1]):
            raise ValueError("BROKER_APPROVAL_DENIED")
        result = database.execute(
            "UPDATE approvals SET status = 'CONSUMED' WHERE id = ? AND status = 'APPROVED' AND token_hash = ?",
            (row[0], token_hash),
        )
        if result.rowcount != 1:
            raise ValueError("BROKER_APPROVAL_REPLAYED")
    return helper_args


def _expired(value: object) -> bool:
    if not isinstance(value, str):
        return True
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return True
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed <= datetime.now(timezone.utc)


def _receive_line(connection: socket.socket) -> bytes:
    buffer = bytearray()
    while len(buffer) <= _MAX_MESSAGE_BYTES:
        block = connection.recv(min(1024, _MAX_MESSAGE_BYTES + 1 - len(buffer)))
        if not block:
            break
        buffer.extend(block)
        if b"\n" in block:
            return bytes(buffer).partition(b"\n")[0]
    raise ValueError("BROKER_MESSAGE_INVALID")


def _unix_socket_family() -> socket.AddressFamily:
    family = getattr(socket, "AF_UNIX", None)
    if family is None:
        raise RuntimeError("BROKER_REQUIRES_UNIX_SOCKET")
    return cast(socket.AddressFamily, family)


def _parse_request(raw: bytes) -> dict[str, object]:
    value = json.loads(raw.decode("utf-8"))
    base_fields = {"version", "action", "service", "user_id", "task_id", "approval_token"}
    if not isinstance(value, dict) or not base_fields.issubset(value) or set(value) - (base_fields | {"change_id"}):
        raise ValueError("BROKER_SCHEMA_INVALID")
    if value.get("version") != _PROTOCOL_VERSION:
        raise ValueError("BROKER_SCHEMA_INVALID")
    if value.get("action") == _ACTION_ROLLBACK and "change_id" not in value:
        raise ValueError("BROKER_SCHEMA_INVALID")
    if value.get("action") == _ACTION_RESTART and "change_id" in value:
        raise ValueError("BROKER_SCHEMA_INVALID")
    return value


def _encode_response(response: BrokerResponse) -> bytes:
    return json.dumps(response.__dict__, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _parse_response(raw: bytes) -> BrokerResponse:
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict) or set(value) != {"returncode", "stdout", "stderr"}:
        raise ValueError("BROKER_RESPONSE_INVALID")
    if not isinstance(value["returncode"], int):
        raise ValueError("BROKER_RESPONSE_INVALID")
    if not isinstance(value["stdout"], str) or not isinstance(value["stderr"], str):
        raise ValueError("BROKER_RESPONSE_INVALID")
    return BrokerResponse(value["returncode"], value["stdout"], value["stderr"])


def main() -> None:
    parser = argparse.ArgumentParser(description="KylinGuard fixed-action execution broker")
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--database-path", type=Path, required=True)
    parser.add_argument("--allowed-client-user", default="kylin-guard")
    args = parser.parse_args()
    serve(args.socket, args.allowed_client_user, args.database_path)


if __name__ == "__main__":
    main()
