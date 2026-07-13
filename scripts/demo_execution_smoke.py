from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx


def login(client: httpx.Client, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}


def approved_execution(
    client: httpx.Client,
    operator: dict[str, str],
    approver: dict[str, str],
    tool_name: str,
    arguments: dict[str, Any],
    *,
    fault: str | None = None,
) -> tuple[httpx.Response, dict[str, Any]]:
    preview = client.post(
        "/api/v1/executions/dry-run",
        headers=operator,
        json={"tool_name": tool_name, "arguments": arguments},
    )
    preview.raise_for_status()
    preview_data = preview.json()["data"]
    if not preview_data["requires_approval"] or not preview_data["requires_backup"]:
        raise RuntimeError("dry-run did not require approval and backup")

    task = client.post(
        "/api/v1/tasks",
        headers=operator,
        json={"goal": f"DEMO 受控执行 {tool_name}", "requested_mode": "DEMO"},
    )
    task.raise_for_status()
    task_id = task.json()["data"]["id"]
    approval = client.post(
        f"/api/v1/tasks/{task_id}/approvals",
        headers=operator,
        json={"tool_name": tool_name, "arguments": arguments},
    )
    approval.raise_for_status()
    decision = client.post(
        f"/api/v1/approvals/{approval.json()['data']['id']}/approve",
        headers=approver,
        json={"reason": "DEMO 隔离资源、影响范围和回滚方案已复核"},
    )
    decision.raise_for_status()
    body: dict[str, Any] = {
        "task_id": task_id,
        "tool_name": tool_name,
        "arguments": arguments,
        "approval_token": decision.json()["data"]["approval_token"],
    }
    if fault is not None:
        body["fault"] = fault
    started = time.perf_counter()
    execution = client.post("/api/v1/executions/run", headers=operator, json=body)
    elapsed_ms = (time.perf_counter() - started) * 1000
    execution.raise_for_status()
    return execution, {"elapsed_ms": round(elapsed_ms, 3), "request_body": body}


def main() -> int:
    base_url = os.getenv("DEMO_TARGET_URL", "").rstrip("/")
    operator_user = os.getenv("DEMO_OPERATOR_USERNAME", "")
    operator_password = os.getenv("DEMO_OPERATOR_PASSWORD", "")
    approver_user = os.getenv("DEMO_APPROVER_USERNAME", "")
    approver_password = os.getenv("DEMO_APPROVER_PASSWORD", "")
    if not all(
        (base_url, operator_user, operator_password, approver_user, approver_password)
    ):
        print("DEMO target and credentials must be supplied through environment variables.")
        return 2

    with httpx.Client(base_url=base_url, timeout=30) as client:
        operator = login(client, operator_user, operator_password)
        approver = login(client, approver_user, approver_password)

        reset = client.post("/api/v1/demo/reset", headers=operator)
        reset.raise_for_status()
        log_arguments = {"candidate_id": reset.json()["data"]["log_candidate_id"]}
        success, success_meta = approved_execution(
            client, operator, approver, "safe_log_cleanup", log_arguments
        )
        success_data = success.json()["data"]
        if success_data["status"] != "SUCCEEDED" or not success_data["backup_ref"]:
            raise RuntimeError("successful cleanup did not produce backup and verification")

        replay = client.post(
            "/api/v1/executions/run",
            headers=operator,
            json=success_meta["request_body"],
        )
        if replay.status_code not in {403, 422}:
            raise RuntimeError("approval replay was not rejected")

        reset = client.post("/api/v1/demo/reset", headers=operator)
        reset.raise_for_status()
        config_arguments = {
            "candidate_id": reset.json()["data"]["config_candidate_id"],
            "content": "server { listen 9090; }\n",
        }
        rolled_back, rollback_meta = approved_execution(
            client,
            operator,
            approver,
            "config_safe_update",
            config_arguments,
            fault="verification",
        )
        rollback_data = rolled_back.json()["data"]
        if rollback_data["status"] != "ROLLED_BACK" or not rollback_data["backup_ref"]:
            raise RuntimeError("verification failure did not roll back from backup")

        service, service_meta = approved_execution(
            client, operator, approver, "service_restart", {"service": "nginx"}
        )
        process, process_meta = approved_execution(
            client, operator, approver, "terminate_process", {"pid": 4242}
        )
        if service.json()["data"]["status"] != "SUCCEEDED":
            raise RuntimeError("DEMO service restart failed")
        if process.json()["data"]["status"] != "SUCCEEDED":
            raise RuntimeError("DEMO process termination failed")

        reset = client.post("/api/v1/demo/reset", headers=operator)
        reset.raise_for_status()
        update_arguments = {
            "candidate_id": reset.json()["data"]["config_candidate_id"],
            "content": "server { listen 7070; }\n",
        }
        updated, update_meta = approved_execution(
            client, operator, approver, "config_safe_update", update_arguments
        )
        updated_data = updated.json()["data"]
        explicit_rollback, explicit_rollback_meta = approved_execution(
            client,
            operator,
            approver,
            "rollback_change",
            {"change_id": updated_data["change_id"]},
        )
        if explicit_rollback.json()["data"]["status"] != "ROLLED_BACK":
            raise RuntimeError("explicit rollback failed")

        audit = client.get("/api/v1/audit/verify", headers=approver)
        audit.raise_for_status()
        if not audit.json()["data"]["valid"]:
            raise RuntimeError("DEMO audit chain is invalid")

    result = {
        "target": base_url,
        "mode": "DEMO",
        "cleanup": {
            "status": success_data["status"],
            "backup_created": bool(success_data["backup_ref"]),
            "verification": success_data["verification"],
            "elapsed_ms": success_meta["elapsed_ms"],
        },
        "approval_replay_status": replay.status_code,
        "verification_failure": {
            "status": rollback_data["status"],
            "backup_created": bool(rollback_data["backup_ref"]),
            "verification": rollback_data["verification"],
            "rollback_status": rollback_data["rollback_status"],
            "elapsed_ms": rollback_meta["elapsed_ms"],
        },
        "service_restart": {
            "status": service.json()["data"]["status"],
            "elapsed_ms": service_meta["elapsed_ms"],
        },
        "terminate_process": {
            "status": process.json()["data"]["status"],
            "elapsed_ms": process_meta["elapsed_ms"],
        },
        "config_update": {
            "status": updated_data["status"],
            "backup_created": bool(updated_data["backup_ref"]),
            "elapsed_ms": update_meta["elapsed_ms"],
        },
        "explicit_rollback": {
            "status": explicit_rollback.json()["data"]["status"],
            "elapsed_ms": explicit_rollback_meta["elapsed_ms"],
        },
        "audit_valid": True,
        "isolated_demo_only": True,
    }
    output = Path("data/demo-execution-acceptance.json")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
