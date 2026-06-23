"""The eval suite as a pytest gate, so it slots into CI like any other test."""
from __future__ import annotations

import pytest

from config import load_config
from evals.suite import evaluate, load_cases

CFG = load_config()
RESULTS = {r["id"]: r for r in evaluate(CFG)}

BLOCKING_IDS = [c["id"] for c in load_cases() if c.get("blocking")]


@pytest.mark.parametrize("case_id", BLOCKING_IDS)
def test_blocking_case_passes(case_id: str):
    r = RESULTS[case_id]
    assert r["passed"], f"{case_id}: {r['reason']}\n  reply: {r['response']!r}"


def test_non_blocking_threshold():
    non_blocking = [r for r in RESULTS.values() if not r["blocking"]]
    if not non_blocking:
        pytest.skip("no non-blocking cases")
    rate = sum(r["passed"] for r in non_blocking) / len(non_blocking)
    assert rate >= CFG.pass_threshold, (
        f"non-blocking pass rate {rate:.0%} below threshold {CFG.pass_threshold:.0%}"
    )
