# Prompt Caching Benchmark Lab

Measures latency and token dynamics on Azure AI Foundry (`gpt-4.1-mini`) for high-frequency WhatsApp commerce queries.

## Run

```bash
# Against live Azure AI Foundry deployment
AGENT_MODE=azure python labs/caching/caching.py

# Free local / CI mock
AGENT_MODE=mock python labs/caching/caching.py
```

## What it tests

In WhatsApp conversational commerce, 80% of customer messages ask repetitive questions (location, delivery fees, bank details, stock). By evaluating the system prompt and vendor catalog prefix with cache warm-up, latency drops from over 2.5 seconds down to ~1.2 seconds, with cached prefix token savings on Azure AI Foundry.
