# Release Gate Lab

Treats a Foundry agent as a versioned, immutable release bundle (`system_prompt.md`
+ `cases.yaml` + pinned model version), automating validation, blocking eval gates,
staging smoke checks, and promotion verdicts.

```bash
AGENT_MODE=mock python labs/release-gate/release_gate.py
AGENT_MODE=azure python labs/release-gate/release_gate.py
```
