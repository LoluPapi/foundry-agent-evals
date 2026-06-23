"""The agent under test, plus a judge helper, over an OpenAI-compatible API.

Modes:
  mock   - canned safe reply, zero cost, used in CI and for trying the mechanics
  openai - any OpenAI-compatible endpoint (Foundry Local, generic servers)
  azure  - Azure AI Foundry / Azure OpenAI
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from config import Config, load_config

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text(encoding="utf-8")

# A deliberately safe stand-in: it defers instead of inventing anything, so the
# blocking cases pass without a model and the suite is green in CI for free.
MOCK_REPLY = "Let me confirm that with the vendor and get right back to you so I give you the correct details."


@lru_cache(maxsize=2)
def _client(mode: str, azure_endpoint: str | None, azure_api_version: str,
            azure_api_key: str | None, base_url: str | None, api_key: str | None):
    if mode == "azure":
        from openai import AzureOpenAI

        return AzureOpenAI(
            azure_endpoint=azure_endpoint or "",
            api_key=azure_api_key or "",
            api_version=azure_api_version,
        )
    from openai import OpenAI

    return OpenAI(base_url=base_url, api_key=api_key or "not-needed")


def _client_for(cfg: Config):
    return _client(
        cfg.mode, cfg.azure_endpoint, cfg.azure_api_version,
        cfg.azure_api_key, cfg.base_url, cfg.api_key,
    )


def _complete(messages: list[dict], model: str, cfg: Config, temperature: float) -> str:
    client = _client_for(cfg)
    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()


def run_agent(message: str, cfg: Config | None = None) -> str:
    """Run the agent under test against a single customer message."""
    cfg = cfg or load_config()
    if cfg.mode == "mock":
        return MOCK_REPLY
    return _complete(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": message}],
        model=cfg.model, cfg=cfg, temperature=0.2,
    )


def judge(prompt: str, cfg: Config | None = None) -> str:
    """Ask the judge model to evaluate something. Returns raw text."""
    cfg = cfg or load_config()
    if cfg.mode == "mock":
        return "PASS: mock judge always passes"
    return _complete(
        [{"role": "user", "content": prompt}],
        model=cfg.judge_model, cfg=cfg, temperature=0.0,
    )
