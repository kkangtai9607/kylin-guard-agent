from __future__ import annotations

import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx


def summarize(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    p95_index = max(0, min(len(ordered) - 1, int(len(ordered) * 0.95) - 1))
    return {
        "iterations": len(values),
        "mean_ms": round(statistics.mean(values), 3),
        "p95_ms": round(ordered[p95_index], 3),
        "max_ms": round(max(values), 3),
    }


def timed(call: Any) -> tuple[float, Any]:
    started = time.perf_counter()
    result = call()
    return (time.perf_counter() - started) * 1000, result


def main() -> int:
    base_url = os.getenv("KYLIN_TARGET_URL", "").rstrip("/")
    username = os.getenv("KYLIN_TARGET_USERNAME", "")
    password = os.getenv("KYLIN_TARGET_PASSWORD", "")
    supplied_token = os.getenv("KYLIN_TARGET_TOKEN", "")
    if not base_url or not supplied_token and (not username or not password):
        print("Target URL and either a short-lived token or credentials are required.")
        return 2

    with httpx.Client(base_url=base_url, timeout=90) as client:
        if supplied_token:
            token = supplied_token
            health = client.get("/api/v1/health")
            health.raise_for_status()
            mode = health.json()["meta"]["mode"]
        else:
            login = client.post(
                "/api/v1/auth/login", json={"username": username, "password": password}
            )
            login.raise_for_status()
            token = login.json()["data"]["access_token"]
            mode = login.json()["meta"]["mode"]
        headers = {"Authorization": f"Bearer {token}"}

        def health_call() -> float:
            elapsed, response = timed(lambda: httpx.get(f"{base_url}/api/v1/health", timeout=10))
            response.raise_for_status()
            return elapsed

        with ThreadPoolExecutor(max_workers=8) as pool:
            health_values = list(pool.map(lambda _: health_call(), range(40)))

        overview_values: list[float] = []
        for _ in range(10):
            elapsed, response = timed(
                lambda: client.get("/api/v1/system/overview", headers=headers)
            )
            response.raise_for_status()
            overview_values.append(elapsed)

        inspection_ms, inspection = timed(
            lambda: client.post("/api/v1/inspections/run", headers=headers)
        )
        inspection.raise_for_status()

        created = client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"goal": "分析当前服务器磁盘空间使用情况，只执行只读诊断"},
        )
        created.raise_for_status()
        task_id = created.json()["data"]["id"]
        diagnosis_ms, diagnosis = timed(
            lambda: client.post(f"/api/v1/tasks/{task_id}/run", headers=headers)
        )
        diagnosis.raise_for_status()
        diagnosis_data = diagnosis.json()["data"]

        audit_ms, audit = timed(lambda: client.get("/api/v1/audit/verify", headers=headers))
        audit.raise_for_status()

    results = {
        "target": base_url,
        "generated_at": time.time(),
        "mode": mode,
        "concurrent_health": summarize(health_values),
        "system_overview": summarize(overview_values),
        "inspection_ms": round(inspection_ms, 3),
        "online_diagnosis_ms": round(diagnosis_ms, 3),
        "diagnosis_status": diagnosis_data["status"],
        "diagnosis_evidence_count": len(diagnosis_data["evidence"]),
        "normalized_evidence_count": len(diagnosis_data.get("normalized_evidence", [])),
        "root_cause_count": len(diagnosis_data.get("root_causes", [])),
        "audit_verify_ms": round(audit_ms, 3),
        "audit_valid": audit.json()["data"]["valid"],
        "notes": [
            "Kylin V11 x86_64 VM result; not LoongArch verification.",
            "All exercised operations were read-only.",
        ],
    }
    output = Path("data/performance-kylin-v11-x86_64.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
