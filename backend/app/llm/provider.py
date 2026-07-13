from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMUnavailableError(RuntimeError):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def generate_structured(self, *, prompt: str, schema: type[SchemaT]) -> SchemaT: ...


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 20,
        max_retries: int = 1,
        circuit_seconds: int = 30,
    ) -> None:
        if not base_url.startswith("https://"):
            raise ValueError("LLM base URL must use HTTPS")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_seconds = circuit_seconds
        self._open_until = 0.0

    def generate_structured(self, *, prompt: str, schema: type[SchemaT]) -> SchemaT:
        if time.monotonic() < self._open_until:
            raise LLMUnavailableError("LLM circuit is open")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return only one JSON object matching this JSON Schema. "
                        "Never emit shell commands or hidden reasoning. JSON Schema: "
                        + json.dumps(schema.model_json_schema(), ensure_ascii=False)
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "temperature": 0,
            "max_tokens": 2048,
        }
        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                response = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return schema.model_validate_json(content)
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
                last_error = error
        self._open_until = time.monotonic() + self.circuit_seconds
        raise LLMUnavailableError("LLM request failed") from last_error


class MockLLMProvider(LLMProvider):
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response

    def generate_structured(self, *, prompt: str, schema: type[SchemaT]) -> SchemaT:
        return schema.model_validate(self.response)


class UnavailableLLMProvider(LLMProvider):
    def generate_structured(self, *, prompt: str, schema: type[SchemaT]) -> SchemaT:
        raise LLMUnavailableError("LLM is not configured")


def provider_from_environment() -> LLMProvider:
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
    if provider not in {"deepseek", "qwen", "openai-compatible"}:
        return UnavailableLLMProvider()
    api_key = os.getenv("DEEPSEEK_API_KEY" if provider == "deepseek" else "LLM_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL" if provider == "deepseek" else "LLM_BASE_URL", "")
    model = os.getenv("DEEPSEEK_MODEL" if provider == "deepseek" else "LLM_MODEL", "")
    if not api_key or not base_url or not model:
        return UnavailableLLMProvider()
    return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)
