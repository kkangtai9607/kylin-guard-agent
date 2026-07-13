from __future__ import annotations

import json
import statistics
import time
from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import create_app
from mcp_server.registry import ToolRegistry


def measure(call: Callable[[], object], iterations: int = 30) -> dict[str, float]:
    values = []
    for _ in range(iterations):
        start = time.perf_counter()
        call()
        values.append((time.perf_counter() - start) * 1000)
    ordered = sorted(values)
    return {
        "mean_ms": round(statistics.mean(values), 3),
        "p95_ms": round(ordered[int(len(ordered) * 0.95) - 1], 3),
        "iterations": iterations,
    }


def main() -> None:
    client = TestClient(create_app())
    registry = ToolRegistry.for_mode("DEMO")
    results = {
        "host": "current-development-host",
        "generated_at": time.time(),
        "health_api": measure(lambda: client.get("/api/v1/health")),
        "system_snapshot_demo": measure(lambda: registry.call("system_snapshot")),
        "capability_probe_demo": measure(lambda: registry.call("capability_probe")),
        "notes": [
            "No remote LLM latency measured without a rotated credential.",
            "Not a Kylin V11 or LoongArch result.",
        ],
    }
    output = Path("data/performance-current-host.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
