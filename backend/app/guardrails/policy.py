from __future__ import annotations

import base64
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any


class RiskLevel(IntEnum):
    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    risk: RiskLevel
    reason_code: str


FORBIDDEN_PATTERNS = (
    r"/etc/(shadow|gshadow)",
    r"\.ssh[/\\].*(id_rsa|id_ed25519|authorized_keys)",
    r"ignore\s+(all|previous).*rules?",
    r"rm\s+-rf\s+[/\\]",
    r"curl\b.*\|\s*(sh|bash)",
    r"wget\b.*\|\s*(sh|bash)",
    r"chmod\s+-R\s+777\s+/(etc|root|boot|usr|var)",
    r"-----BEGIN\s+(OPENSSH|RSA|EC|DSA)\s+PRIVATE\s+KEY-----",
    r"(show|read|dump|cat|读取|显示).{0,24}(api[_ -]?key|token|password|私钥|密钥|凭据)",
    r"(ignore|reveal|print|show).{0,24}(system|developer).{0,12}(prompt|message|instructions?)",
    r"(显示|泄露|输出).{0,24}(system\s+prompt|developer\s+message|系统提示词)",
    r"(忽略|绕过|关闭|跳过).{0,18}(规则|护栏|审批|安全策略|权限)",
    r"(?:\$\(|`[^`]+`|\|\||&&|[|><])",
)


class PolicyEngine:
    def classify_input(self, text: str) -> PolicyDecision:
        normalized = unicodedata.normalize("NFKC", self._decode_once(text))
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in FORBIDDEN_PATTERNS):
            return PolicyDecision(False, RiskLevel.L4, "FORBIDDEN_INPUT")
        if "UNTRUSTED_DATA" in normalized:
            return PolicyDecision(True, RiskLevel.L2, "UNTRUSTED_DATA_ISOLATED")
        return PolicyDecision(True, RiskLevel.L0, "INPUT_ACCEPTED")

    def authorize_tool(
        self,
        *,
        user_goal: str,
        tool_name: str,
        read_only: bool,
        server_mode: str,
        model_risk: RiskLevel | None = None,
    ) -> PolicyDecision:
        input_decision = self.classify_input(user_goal)
        if not input_decision.allowed:
            return input_decision
        deterministic = RiskLevel.L1 if read_only else RiskLevel.L3
        risk = max(deterministic, model_risk or RiskLevel.L0)
        if not read_only and server_mode not in {"DEMO", "CONTROLLED_EXECUTION"}:
            return PolicyDecision(False, risk, "MODE_FORBIDDEN")
        if any(value in tool_name.lower() for value in ("shell", "command", "script")):
            return PolicyDecision(False, RiskLevel.L4, "GENERIC_EXECUTION_FORBIDDEN")
        return PolicyDecision(True, risk, "POLICY_ALLOWED")

    @staticmethod
    def _decode_once(text: str) -> str:
        compact = "".join(text.split())
        if len(compact) >= 16 and re.fullmatch(r"[A-Za-z0-9+/=]+", compact):
            try:
                decoded = base64.b64decode(compact, validate=True).decode("utf-8")
                return f"{text}\n{decoded}"
            except (ValueError, UnicodeDecodeError):
                pass
        return text


class PathGuard:
    def __init__(self, allowed_roots: tuple[Path, ...], protected_paths: tuple[Path, ...]) -> None:
        self.allowed_roots = tuple(path.resolve() for path in allowed_roots)
        self.protected_paths = tuple(path.resolve() for path in protected_paths)

    def validate(self, raw_path: str, *, must_exist: bool = True) -> Path:
        if "\x00" in raw_path:
            raise ValueError("PATH_REJECTED")
        source = Path(raw_path)
        absolute_source = source if source.is_absolute() else Path.cwd() / source
        current_source = absolute_source
        while current_source != current_source.parent:
            if current_source.is_symlink():
                raise ValueError("SYMLINK_REJECTED")
            current_source = current_source.parent
        target = source.resolve(strict=must_exist)
        if target in self.protected_paths or any(
            path in target.parents for path in self.protected_paths
        ):
            raise ValueError("PROTECTED_PATH")
        if not any(target == root or root in target.parents for root in self.allowed_roots):
            raise ValueError("PATH_REJECTED")
        return target


def canonical_arguments(arguments: Mapping[str, Any]) -> str:
    import json

    return json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
