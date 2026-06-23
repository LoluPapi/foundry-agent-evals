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

# Token accounting for the whole run (agent calls + judge calls), so the gate
# can report real usage and a cost estimate.
USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}


def reset_usage() -> None:
    for k in USAGE:
        USAGE[k] = 0

# Markers that flag a prompt-injection / instruction-override attempt. Kept
# lower-case; matched against the lower-cased customer message.
_INJECTION_MARKERS = (
    "ignore your", "ignore previous", "giveaway",
    "reply with the code", "you are now", "system prompt",
)

# A decisive, no-hedge refusal for injection attempts. It declines clearly and
# never echoes any injected code, so the ignores_injection grader is satisfied.
_MOCK_INJECTION_REPLY = (
    "I can only help with this vendor's products and orders, so I won't do that. "
    "What can I get sorted for you today?"
)


def _mock_reply(message: str) -> str:
    """Deterministic stand-in for CI / free runs.

    Mirrors StratiSell's zero-hedge style: refuse injections decisively, and
    otherwise confirm the concrete detail by echoing the customer's message so
    the expectation tokens are present, while avoiding every forbidden hedge.
    """
    low = message.lower()
    if any(marker in low for marker in _INJECTION_MARKERS):
        return _MOCK_INJECTION_REPLY
    return f"Absolutely, I've got that: {message} I'm sorting it for you right now."


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
    if resp.usage:
        USAGE["prompt_tokens"] += resp.usage.prompt_tokens
        USAGE["completion_tokens"] += resp.usage.completion_tokens
        USAGE["total_tokens"] += resp.usage.total_tokens
        USAGE["calls"] += 1
    return (resp.choices[0].message.content or "").strip()


# Sentinel returned when the platform's content filter blocks a request. This
# is a real, common outcome on Azure (e.g. a jailbreak attempt), and from the
# agent's point of view it is a safe refusal, not a crash.
CONTENT_FILTERED = "[blocked by content filter]"


def run_agent(message: str, cfg: Config | None = None) -> str:
    """Run the agent under test against a single customer message."""
    cfg = cfg or load_config()
    if cfg.mode == "mock":
        return _mock_reply(message)
    try:
        return _complete(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": message}],
            model=cfg.model, cfg=cfg, temperature=0.2,
        )
    except Exception as e:  # noqa: BLE001 - we only swallow content-filter blocks
        msg = str(e).lower()
        if "content_filter" in msg or "content management" in msg:
            return CONTENT_FILTERED
        raise


def judge(prompt: str, cfg: Config | None = None) -> str:
    """Ask the judge model to evaluate something. Returns raw text."""
    cfg = cfg or load_config()
    if cfg.mode == "mock":
        return "PASS: mock judge always passes"
    return _complete(
        [{"role": "user", "content": prompt}],
        model=cfg.judge_model, cfg=cfg, temperature=0.0,
    )
