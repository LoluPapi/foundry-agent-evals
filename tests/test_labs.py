"""Smoke tests for the mock-mode lab scripts under labs/."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_lab(rel_path: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "AGENT_MODE": "mock", "PASS_THRESHOLD": "0.80"}
    env.pop("RENDER_PNG", None)
    return subprocess.run(
        [sys.executable, rel_path],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_prompt_shields_mock():
    res = _run_lab("labs/prompt-shields/prompt_shields.py")
    assert res.returncode == 0, res.stderr
    assert "6/6 inputs handled safely" in res.stdout


def test_rbac_principal_mock():
    res = _run_lab("labs/rbac-principal/rbac_check.py")
    assert res.returncode == 0, res.stderr
    assert "403 AuthorizationFailed" in res.stdout


def test_release_gate_mock():
    res = _run_lab("labs/release-gate/release_gate.py")
    assert res.returncode == 0, res.stderr
    assert "RELEASE: PROMOTE" in res.stdout


def test_regression_diff_mock_blocks_pidgin_drop():
    res = _run_lab("labs/regression-diff/regression_diff.py")
    assert res.returncode == 1, res.stdout
    assert "BLOCK upgrade" in res.stdout


def test_ops_triage_mock():
    res = _run_lab("labs/ops-triage/ops_triage.py")
    assert res.returncode == 0, res.stderr
    assert "HUMAN_GATE" in res.stdout
    assert "0 irreversible auto-runs" in res.stdout
