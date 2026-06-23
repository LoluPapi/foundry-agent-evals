#!/usr/bin/env python
"""Run the eval suite as a gate. Exits non-zero if it does not pass.

  AGENT_MODE=mock python run_evals.py
"""
from __future__ import annotations

import json
import sys

from agent import agent
from config import load_config
from evals.suite import evaluate, summarize


def main() -> int:
    cfg = load_config()
    agent.reset_usage()
    results = evaluate(cfg)
    summary = summarize(results, cfg.pass_threshold)

    u = agent.USAGE
    est_cost = (
        u["prompt_tokens"] / 1_000_000 * cfg.price_in_per_1m
        + u["completion_tokens"] / 1_000_000 * cfg.price_out_per_1m
    )

    print(f"\nEval suite  (mode={cfg.mode}, model={cfg.model})\n" + "-" * 60)
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        block = "block" if r["blocking"] else "  -  "
        print(f"  [{mark}] {block}  {r['id']:<28} {r['reason']}")

    print("-" * 60)
    print(f"  total {summary['passed']}/{summary['total']} passed")
    print(f"  non-blocking rate {summary['non_blocking_rate']:.0%} "
          f"(threshold {summary['threshold']:.0%})")
    if summary["blocking_failed"]:
        ids = ", ".join(r["id"] for r in summary["blocking_failed"])
        print(f"  BLOCKING FAILURES: {ids}")

    if cfg.mode != "mock":
        print(f"  tokens: {u['total_tokens']} "
              f"({u['prompt_tokens']} in / {u['completion_tokens']} out) "
              f"over {u['calls']} model calls")
        print(f"  est. cost this run: ${est_cost:.4f} "
              f"(at ${cfg.price_in_per_1m}/M in, ${cfg.price_out_per_1m}/M out)")

    with open("results.json", "w", encoding="utf-8") as fh:
        json.dump({"results": results, "summary": {
            **{k: v for k, v in summary.items() if k != "blocking_failed"},
            "usage": u,
            "est_cost_usd": round(est_cost, 6),
        }}, fh, indent=2, ensure_ascii=False)

    if summary["ok"]:
        print("\n  GATE: pass\n")
        return 0
    print("\n  GATE: fail\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
