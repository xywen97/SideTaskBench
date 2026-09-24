"""Load credentials without copying secrets into experiment artifacts."""

from dataclasses import dataclass, field
from pathlib import Path
import os
from urllib.parse import urlparse

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    timeout_seconds: float = 300.0
    retries: int = 3
    thinking: str = "default"

    @classmethod
    def load(cls, env_file: Path) -> "Settings":
        values = {**dotenv_values(env_file), **os.environ}
        key = values.get("DEEPSEEK_API_KEY", "")
        base = str(values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")).rstrip("/")
        model = str(values.get("DEEPSEEK_MODEL", "deepseek-v4-flash"))
        if not key:
            raise ValueError("DEEPSEEK_API_KEY is missing; configure the local .env file.")
        parsed = urlparse(base)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("DEEPSEEK_BASE_URL must be an HTTP(S) URL without embedded credentials or a query.")
        return cls(api_key=str(key), base_url=base, model=model)

    def public_metadata(self) -> dict:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "request_retries": self.retries,
            "max_tokens_parameter": "omitted",
            "token_budget": None,
            "thinking": self.thinking,
        }
