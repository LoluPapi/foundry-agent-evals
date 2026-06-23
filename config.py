"""Environment-driven config. Keeps the rest of the code free of os.getenv noise."""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Config:
    mode: str  # "mock" | "openai" | "azure"
    model: str
    judge_model: str
    pass_threshold: float

    # openai-compatible
    base_url: str | None
    api_key: str | None

    # azure
    azure_endpoint: str | None
    azure_api_key: str | None
    azure_api_version: str


def load_config() -> Config:
    mode = os.getenv("AGENT_MODE", "mock").strip().lower()
    model = os.getenv("MODEL", "gpt-4o-mini")
    return Config(
        mode=mode,
        model=model,
        judge_model=os.getenv("JUDGE_MODEL", model),
        pass_threshold=float(os.getenv("PASS_THRESHOLD", "0.8")),
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
    )
