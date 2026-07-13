from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass

from backend.app.guardrails.policy import canonical_arguments


@dataclass(frozen=True)
class ApprovalClaims:
    user_id: str
    task_id: str
    tool_name: str
    arguments_hash: str
    risk_level: str
    expires_at: int
    nonce: str


class ApprovalTokenManager:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < 32:
            raise ValueError("approval secret must contain at least 32 bytes")
        self.secret = secret
        self._consumed: set[str] = set()

    def issue(
        self,
        user_id: str,
        task_id: str,
        tool_name: str,
        arguments: Mapping[str, object],
        ttl: int = 300,
    ) -> str:
        claims = ApprovalClaims(
            user_id,
            task_id,
            tool_name,
            hashlib.sha256(canonical_arguments(arguments).encode()).hexdigest(),
            "L3",
            int(time.time()) + ttl,
            secrets.token_urlsafe(24),
        )
        payload = json.dumps(asdict(claims), sort_keys=True, separators=(",", ":"))
        signature = hmac.new(self.secret, payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}.{signature}"

    def consume(
        self,
        token: str,
        *,
        user_id: str,
        task_id: str,
        tool_name: str,
        arguments: Mapping[str, object],
    ) -> ApprovalClaims:
        try:
            payload, signature = token.rsplit(".", 1)
            expected = hmac.new(self.secret, payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("APPROVAL_TAMPERED")
            claims = ApprovalClaims(**json.loads(payload))
        except (TypeError, KeyError, json.JSONDecodeError) as error:
            raise ValueError("APPROVAL_INVALID") from error
        if claims.nonce in self._consumed:
            raise ValueError("APPROVAL_REPLAYED")
        if claims.expires_at < int(time.time()):
            raise ValueError("APPROVAL_EXPIRED")
        actual_hash = hashlib.sha256(canonical_arguments(arguments).encode()).hexdigest()
        if (claims.user_id, claims.task_id, claims.tool_name, claims.arguments_hash) != (
            user_id,
            task_id,
            tool_name,
            actual_hash,
        ):
            raise ValueError("APPROVAL_SCOPE_MISMATCH")
        self._consumed.add(claims.nonce)
        return claims
