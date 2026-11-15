# Ops Triage & Human-in-the-Loop Boundary Lab

Uses Azure AI Foundry (`gpt-4.1-mini`, JSON mode) to triage incoming ops alerts
and classify risk, then enforces a hard deterministic policy line: read-only
diagnostics and safe restarts can draft or run, while money, RBAC, and delete
actions are always held behind a human gate.

```bash
AGENT_MODE=mock python labs/ops-triage/ops_triage.py
AGENT_MODE=azure python labs/ops-triage/ops_triage.py
```
