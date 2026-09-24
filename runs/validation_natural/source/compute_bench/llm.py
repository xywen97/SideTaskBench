"""Real Chat Completions calls; no simulated responses or token caps."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import time

import httpx

from .config import Settings


class LLMError(RuntimeError):
    pass


class ChatClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.Client(timeout=httpx.Timeout(settings.timeout_seconds, connect=30))

    def close(self):
        self.client.close()

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> tuple[dict, dict]:
        body = {"model": self.settings.model, "messages": messages}
        if self.settings.thinking != "default":
            body["thinking"] = {"type": self.settings.thinking}
        if tools:
            body.update(tools=tools, tool_choice="auto")
        # Intentionally omit max_tokens/max_completion_tokens and any cumulative token cap.
        request_hash = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        started = time.monotonic()
        errors = []
        for attempt in range(self.settings.retries + 1):
            try:
                response = self.client.post(
                    self.settings.base_url + "/chat/completions",
                    headers={"Authorization": "Bearer " + self.settings.api_key},
                    json=body,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    raise LLMError(f"Transient API HTTP {response.status_code}")
                if response.is_error:
                    # Never echo an upstream body or request headers into logs.
                    raise ValueError(f"API rejected request: HTTP {response.status_code}")
                data = response.json()
                choice = data["choices"][0]
                message = choice["message"]
                metadata = {
                    "request_sha256": request_hash,
                    "response_id": data.get("id"),
                    "model": data.get("model", self.settings.model),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "usage": data.get("usage", {}),
                    "finish_reason": choice.get("finish_reason"),
                    "latency_seconds": round(time.monotonic() - started, 3),
                    "attempts": attempt + 1,
                    "transient_errors": errors,
                }
                if choice.get("finish_reason") == "length":
                    metadata["provider_truncated"] = True
                return message, metadata
            except (httpx.TransportError, LLMError) as exc:
                errors.append(type(exc).__name__)
                if attempt == self.settings.retries:
                    raise LLMError(f"LLM transport unavailable after {attempt + 1} attempts ({type(exc).__name__}).") from None
                time.sleep(min(2 ** attempt, 16))
        raise LLMError("Unreachable retry state")
