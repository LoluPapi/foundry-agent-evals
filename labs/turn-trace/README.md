# Turn Reconstruction & Observability Lab

Demonstrates OpenTelemetry-style span instrumentation and forensic incident reconstruction for Azure AI Foundry conversational agents.

## Run

```bash
# Against live Azure AI Foundry deployment
AGENT_MODE=azure python labs/turn-trace/turn_trace.py

# Free local / CI mock
AGENT_MODE=mock python labs/turn-trace/turn_trace.py
```

## What it tests

When an agent quotes the wrong price or exhibits behavioral drift at 3:00 AM, traditional HTTP status codes (200 OK) tell you nothing. This lab shows how decomposing the turn into explicit spans (`intent.classify`, `tool.catalog_search`, `llm.completion`, `policy.margin_guard`) gives you an unforgeable audit trail to diagnose prompt drift, tool failure, or customer prompt injection.
