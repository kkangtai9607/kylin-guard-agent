from __future__ import annotations

import hashlib
from dataclasses import dataclass
from difflib import unified_diff


@dataclass(frozen=True)
class DriftResult:
    changed: bool
    baseline_hash: str
    current_hash: str
    diff_summary: list[str]


def detect_drift(baseline: str, current: str, max_lines: int = 50) -> DriftResult:
    baseline_hash = hashlib.sha256(baseline.encode()).hexdigest()
    current_hash = hashlib.sha256(current.encode()).hexdigest()
    diff = list(unified_diff(baseline.splitlines(), current.splitlines(), lineterm=""))[:max_lines]
    return DriftResult(
        baseline_hash != current_hash,
        baseline_hash,
        current_hash,
        [redact_line(line) for line in diff],
    )


def redact_line(line: str) -> str:
    lowered = line.lower()
    if any(
        marker in lowered for marker in ("password", "token", "secret", "api_key", "authorization")
    ):
        prefix = line[:1] if line[:1] in {"+", "-", " "} else ""
        return f"{prefix}***REDACTED***"
    return line[:500]
