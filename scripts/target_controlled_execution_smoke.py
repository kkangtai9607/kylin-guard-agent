from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx


def require_env(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def login(client: httpx.Client, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    response.raise_for_status()
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def assert_no_error(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if payload.get("error") is not None:
        raise RuntimeError(json.dumps(payload["error"], ensure_ascii=False))
    return payload["data"]


def main() -> int:
    base_url = os.getenv("KG_TARGET_URL", "http://127.0.0.1:8000").rstrip("/")
    operator_username = os.getenv("KG_TEST_OPERATOR_USERNAME", "final-op")
    approver_username = os.getenv("KG_TEST_APPROVER_USERNAME", "final-ap")
    operator_password = require_env("KG_TEST_OPERATOR_PASSWORD")
    approver_password = require_env("KG_TEST_APPROVER_PASSWORD")

    with httpx.Client(base_url=base_url, timeout=60) as client:
        health = client.get("/api/v1/health")
        health.raise_for_status()
        mode = health.json()["meta"]["mode"]
        if mode != "CONTROLLED_EXECUTION":
            raise RuntimeError(f"expected CONTROLLED_EXECUTION, got {mode}")

        operator = login(client, operator_username, operator_password)
        approver = login(client, approver_username, approver_password)

        preview = assert_no_error(
            client.post(
                "/api/v1/executions/dry-run",
                headers=operator,
                json={"tool_name": "service_restart", "arguments": {"service": "nginx"}},
            )
        )
        if preview["risk_level"] != "L3" or not preview["requires_approval"]:
            raise RuntimeError(f"unexpected dry-run preview: {preview}")

        task = assert_no_error(
            client.post(
                "/api/v1/tasks",
                headers=operator,
                json={
                    "goal": "Validate controlled nginx restart through fixed broker.",
                    "requested_mode": "CONTROLLED_EXECUTION",
                },
            )
        )
        task_id = task["id"]

        approval = assert_no_error(
            client.post(
                f"/api/v1/tasks/{task_id}/approvals",
                headers=operator,
                json={"tool_name": "service_restart", "arguments": {"service": "nginx"}},
            )
        )
        approval_id = approval["id"]

        approved = assert_no_error(
            client.post(
                f"/api/v1/approvals/{approval_id}/approve",
                headers=approver,
                json={"reason": "fixed nginx restart helper validated for final smoke"},
            )
        )
        if approved["status"] != "APPROVED":
            raise RuntimeError(f"approval not approved: {approved['status']}")

        claimed = assert_no_error(
            client.post(f"/api/v1/approvals/{approval_id}/claim", headers=operator)
        )
        token = claimed["approval_token"]
        body = {
            "task_id": task_id,
            "tool_name": "service_restart",
            "arguments": {"service": "nginx"},
            "approval_token": token,
        }

        started = time.perf_counter()
        execution = assert_no_error(
            client.post("/api/v1/executions/run", headers=operator, json=body)
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        if execution["status"] != "SUCCEEDED":
            raise RuntimeError(f"execution did not succeed: {execution}")

        replay = client.post("/api/v1/executions/run", headers=operator, json=body)
        if replay.status_code != 403:
            raise RuntimeError(f"approval replay was not rejected: HTTP {replay.status_code}")

        audit = assert_no_error(client.get("/api/v1/audit/verify", headers=approver))
        if not audit["valid"]:
            raise RuntimeError("audit hash chain is invalid")

    result = {
        "target": base_url,
        "mode": "CONTROLLED_EXECUTION",
        "task_id": task_id,
        "approval_id": approval_id,
        "change_id": execution.get("change_id"),
        "execution_status": execution["status"],
        "verification": execution.get("verification"),
        "approval_replay_status": replay.status_code,
        "audit_valid": True,
        "elapsed_ms": elapsed_ms,
        "notes": [
            "Kylin V11 x86_64 target smoke; not LoongArch verification.",
            "Approval token and passwords are intentionally omitted.",
        ],
    }
    output_path = os.getenv("KG_RESULT_PATH")
    if output_path:
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
