# Model Right-Sizing Benchmark Lab

Evaluates whether `gpt-4.1-mini` on Azure AI Foundry has sufficient reasoning and policy adherence for mission-critical WhatsApp conversational commerce, while cutting token cost by up to 95% compared to flagship models.

## Run

```bash
# Against live Azure AI Foundry deployment
AGENT_MODE=azure python labs/model-bench/model_bench.py

# Free local / CI mock
AGENT_MODE=mock python labs/model-bench/model_bench.py
```

## What it tests

Evaluates 6 core commerce behaviors:
1. Multi-item arithmetic and delivery zone calculation
2. Platform-level prompt injection resistance
3. Floor price defense against lowball bargaining
4. Fake bank alert and premature goods release refusal
5. Out-of-catalog boundary handling
6. Account integrity (zero hallucination of payment details)
