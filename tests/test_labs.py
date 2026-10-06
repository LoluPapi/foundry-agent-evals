"""Smoke tests for labs running under AGENT_MODE=mock."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_script(script_rel_path: str):
    env = dict(os.environ)
    env["AGENT_MODE"] = "mock"
    script = REPO_ROOT / script_rel_path
    assert script.exists(), f"Script {script} does not exist"
    res = subprocess.run(
        [sys.executable, str(script)],
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Script {script} failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"


def test_haggling_mock():
    _run_script("labs/haggling/haggling.py")


def test_caching_mock():
    _run_script("labs/caching/caching.py")


def test_turn_trace_mock():
    _run_script("labs/turn-trace/turn_trace.py")


def test_model_bench_mock():
    _run_script("labs/model-bench/model_bench.py")
