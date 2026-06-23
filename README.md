# foundry-agent-evals

A small, runnable lab for treating **agent evaluations as a blocking CI gate**,
the way unit tests gate normal code. It runs an eval suite against an
OpenAI-compatible chat model (Azure AI Foundry, Foundry Local, Azure OpenAI, or
a mock), grades the results, and **fails the build** when a blocking case
regresses.

It is deliberately cheap to run: a tiny eval set, a small model, and a free
local/mock mode so the suite is green in CI without spending anything.

> Companion write-up: "Evaluations are the test suite" on
> [mololuwa.com/writing](https://mololuwa.com/writing).

## The idea

An agent is never right 100% of the time, so "passing" is a number you choose
and defend. This repo encodes that choice:

- The **eval set** (`evals/cases.yaml`) is the spec. It is just cases: an input
  that looks like a real message, the behaviour you expect, and a grader.
- **Blocking** cases (safety, payments) must stay green. One regression fails
  the build.
- **Non-blocking** cases (open-ended conversation) are held to a defended
  threshold, not perfection.

## Layout

```
agent/
  system_prompt.md     the agent persona (a StratiSell-style sales assistant)
  agent.py             thin client over an OpenAI-compatible endpoint
evals/
  cases.yaml           starter eval cases (replace with your real ones)
  graders.py           grader functions (refusal, contains, llm-judge, ...)
run_evals.py           runs the suite, prints a report, exits non-zero on fail
tests/
  test_evals.py        the same suite as a pytest gate
.github/workflows/
  evals.yml            runs the gate in CI (mock mode, no secrets needed)
config.py              reads mode + endpoint from the environment
```

## Quick start (free, no Azure needed)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# mock mode: canned responses, zero cost, good for trying the mechanics
AGENT_MODE=mock python run_evals.py
AGENT_MODE=mock pytest -q
```

## Running against a real model, cheaply

Set the mode and endpoint in `.env` (see `.env.example`). Three honest options,
cheapest first:

1. **Foundry Local** (free, on-device): run a small model locally and point
   `OPENAI_BASE_URL` at it. No token cost. Best for the dev loop.
2. **Azure AI Foundry / Azure OpenAI** (cheap, pay-per-token): deploy a small
   model such as `gpt-4o-mini` as **serverless**, keep the eval set tiny, and a
   full run costs cents. This is the one that produces real numbers for a
   Foundry write-up.
3. **Any OpenAI-compatible endpoint**: works too.

```bash
# example: pay-per-token cloud run
AGENT_MODE=openai python run_evals.py
```

### Keep it cheap

- Set an Azure **budget + spending limit** before you deploy anything.
- Use a **small model** and a **small eval set** (10 to 20 cases).
- Prefer **serverless / pay-per-token** over provisioned capacity.
- **Undeploy** endpoints when idle.

## Plugging in the Azure AI Evaluation SDK

`evals/graders.py` is intentionally simple so the mechanics are clear. To use
Microsoft's evaluators (groundedness, relevance, safety, and friends), swap the
grader body for `azure-ai-evaluation` calls. The case format and the CI gate do
not change. That mapping is the subject of the follow-up article.

## License

MIT. See `LICENSE`.
