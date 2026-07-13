from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SECRET_PATTERNS = (
    (re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer ***REDACTED***"),
    (re.compile(r"\bsk-[A-Za-z0-9]{12,}\b"), "sk-***REDACTED***"),
    (
        re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s,;]+"),
        r"\1=***REDACTED***",
    ),
)
INJECTION_MARKERS = re.compile(
    r"(?i)(ignore\s+(all|previous)|system\s+prompt|developer\s+message|"
    r"run\s+rm\s+-rf|execute\s+(shell|command)|绕过.{0,8}(规则|审批)|忽略.{0,8}规则)"
)


def sanitize_untrusted(value: Any, *, max_text_bytes: int = 32768, depth: int = 0) -> Any:
    """Bound and redact external data without interpreting it as instructions."""
    if depth > 8:
        return "[TRUNCATED_DEPTH]"
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 200:
                result["_truncated"] = True
                break
            normalized_key = sanitize_text(str(key), max_text_bytes=256)
            if any(marker in normalized_key.lower() for marker in ("password", "token", "secret", "api_key", "authorization", "private_key")):
                result[normalized_key] = "***REDACTED***"
            else:
                result[normalized_key] = sanitize_untrusted(
                    item, max_text_bytes=max_text_bytes, depth=depth + 1
                )
        return result
    if isinstance(value, (list, tuple)):
        return [
            sanitize_untrusted(item, max_text_bytes=max_text_bytes, depth=depth + 1)
            for item in value[:200]
        ]
    if isinstance(value, str):
        return sanitize_text(value, max_text_bytes=max_text_bytes)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize_text(str(value), max_text_bytes=max_text_bytes)


def sanitize_text(value: str, *, max_text_bytes: int = 32768) -> str:
    result = CONTROL_CHARACTERS.sub("", value)
    for pattern, replacement in SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    encoded = result.encode("utf-8", errors="replace")
    if len(encoded) > max_text_bytes:
        result = encoded[:max_text_bytes].decode("utf-8", errors="ignore") + "…[TRUNCATED]"
    return result


def contains_instruction_like_data(value: Any) -> bool:
    return bool(INJECTION_MARKERS.search(str(value)))
