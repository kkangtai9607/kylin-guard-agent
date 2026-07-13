from __future__ import annotations

import uuid
from pathlib import Path

from backend.app.executor.controlled import DemoControlledExecutor
from backend.app.guardrails.approval import ApprovalTokenManager


class DemoExecutionService:
    def __init__(self) -> None:
        self.executor: DemoControlledExecutor | None = None

    def reset(self, secret: bytes) -> dict[str, str]:
        root = Path("demo/runtime") / str(uuid.uuid4())
        root.mkdir(parents=True, exist_ok=False)
        log = root / "old-app.log"
        config = root / "nginx.conf"
        log.write_text("DEMO archived application log\n" * 100, encoding="utf-8")
        config.write_text("server { listen 8080; }\n", encoding="utf-8")
        self.executor = DemoControlledExecutor(root, ApprovalTokenManager(secret))
        return {
            "log_candidate_id": self.executor.register_candidate(log),
            "config_candidate_id": self.executor.register_candidate(config),
            "sandbox_id": root.name,
        }

    def require_executor(self) -> DemoControlledExecutor:
        if self.executor is None:
            raise ValueError("DEMO_NOT_INITIALIZED")
        return self.executor


demo_execution_service = DemoExecutionService()
