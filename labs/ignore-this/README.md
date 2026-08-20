# Ignore this

A small red-team lab that throws "ignore your previous instructions" style
attacks at the sales agent persona, and checks that the reply never complies.

```bash
# from the foundry-agent-evals repo root, venv active
AGENT_MODE=azure python labs/ignore-this/ignore_this.py
AGENT_MODE=mock  python labs/ignore-this/ignore_this.py
```

Companion write-up: "Ignore your previous instructions" on mololuwa.com.
