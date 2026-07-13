from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel):
    request_id: str
    data: Any | None = None
    error: ErrorBody | None = None
    meta: dict[str, Any]
