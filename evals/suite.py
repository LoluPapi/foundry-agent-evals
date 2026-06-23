"""Load cases, run the agent over them, grade, and summarize."""
from __future__ import annotations

from pathlib import Path

import yaml

from agent.agent import run_agent
from config import Config, load_config
from evals.graders import grade

CASES_PATH = Path(__file__).parent / "cases.yaml"


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def run_case(case: dict, cfg: Config) -> dict:
    response = run_agent(case["input"], cfg)
    passed, reason = grade(case, response, cfg)
    return {
        "id": case["id"],
        "category": case.get("category", "?"),
        "blocking": bool(case.get("blocking", False)),
        "passed": bool(passed),
        "reason": reason,
        "response": response,
    }


def evaluate(cfg: Config | None = None) -> list[dict]:
    cfg = cfg or load_config()
    return [run_case(c, cfg) for c in load_cases()]


def summarize(results: list[dict], threshold: float) -> dict:
    blocking = [r for r in results if r["blocking"]]
    non_blocking = [r for r in results if not r["blocking"]]
    blocking_failed = [r for r in blocking if not r["passed"]]
    nb_pass = sum(r["passed"] for r in non_blocking)
    nb_rate = (nb_pass / len(non_blocking)) if non_blocking else 1.0
    ok = not blocking_failed and nb_rate >= threshold
    return {
        "ok": ok,
        "blocking_failed": blocking_failed,
        "non_blocking_rate": nb_rate,
        "threshold": threshold,
        "total": len(results),
        "passed": sum(r["passed"] for r in results),
    }
