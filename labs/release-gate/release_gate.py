from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent import agent  # noqa: E402
from config import load_config  # noqa: E402
from evals.suite import evaluate, summarize  # noqa: E402
from labs.terminal_render import maybe_render_terminal  # noqa: E402


def bundle_digest(model_pin: str) -> str:
    h = hashlib.sha256()
    for rel in ("agent/system_prompt.md", "evals/cases.yaml"):
        h.update((REPO_ROOT / rel).read_bytes())
    h.update(model_pin.encode())
    return h.hexdigest()[:12]


def main() -> int:
    cfg = load_config()
    model_pin = os.getenv("MODEL_PIN", f"{cfg.model}@2025-04-14")
    upgrade_policy = os.getenv("VERSION_UPGRADE_POLICY", "NoAutoUpgrade")

    lines: list[tuple[str, str]] = [
        (f"$ python labs/release-gate/release_gate.py  (mode={cfg.mode})", "white"),
        (f"Artifact: {model_pin} | upgrade={upgrade_policy}", "muted"),
        ("-" * 74, "muted"),
    ]

    t0 = time.perf_counter()
    digest = bundle_digest(model_pin)
    pinned_ok = upgrade_policy != "OnceNewDefaultVersionAvailable"
    s1 = f"  [{'PASS' if pinned_ok else 'FAIL'}] stage 1 validate    bundle=sha256:{digest}  pin={model_pin}"
    lines.append((s1, "green" if pinned_ok else "red"))

    agent.reset_usage()
    results = evaluate(cfg)
    summary = summarize(results, cfg.pass_threshold)
    eval_ok = summary["ok"]
    s2 = (
        f"  [{'PASS' if eval_ok else 'FAIL'}] stage 2 eval-gate   "
        f"passed={summary['passed']}/{summary['total']}  "
        f"open={summary['non_blocking_rate']:.0%} (min {summary['threshold']:.0%})"
    )
    lines.append((s2, "green" if eval_ok else "red"))

    smoke_reply = agent.run_agent(
        "I want to order the green ankara dress for Friday, is it 18,500?", cfg
    )
    smoke_ok = (
        smoke_reply != agent.CONTENT_FILTERED
        and len(smoke_reply.strip()) > 10
        and "error" not in smoke_reply.lower()
    )
    snippet = smoke_reply.replace("\n", " ")[:44]
    s3 = f"  [{'PASS' if smoke_ok else 'FAIL'}] stage 3 smoke-test  \"{snippet}...\""
    lines.append((s3, "green" if smoke_ok else "red"))

    elapsed = time.perf_counter() - t0
    u = agent.USAGE
    cost = (
        u["prompt_tokens"] / 1_000_000 * cfg.price_in_per_1m
        + u["completion_tokens"] / 1_000_000 * cfg.price_out_per_1m
    )
    promote_ok = pinned_ok and eval_ok and smoke_ok
    s4 = (
        f"  [{'PASS' if promote_ok else 'FAIL'}] stage 4 promote     "
        f"verdict={'READY_FOR_PROD' if promote_ok else 'BLOCKED'}  "
        f"tokens={u['total_tokens']}  cost=${cost:.4f}  ({elapsed:.1f}s)"
    )
    lines.append((s4, "green" if promote_ok else "red"))
    lines.append(("-" * 74, "muted"))
    lines.append((
        f"  RELEASE: {'PROMOTE sha256:' + digest if promote_ok else 'BLOCKED'}",
        "green" if promote_ok else "red",
    ))

    for text, _ in lines:
        print(text)

    maybe_render_terminal("Foundry Agent CI/CD - Validate, Eval Gate, Smoke, Promote", lines)
    return 0 if promote_ok else 1


if __name__ == "__main__":
    sys.exit(main())
