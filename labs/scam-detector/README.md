# scam-detector

A tiny lab: hand a model ~12 short text messages and ask it to flag the scams.

Each message gets a verdict (`SCAM`, `SUSPICIOUS`, or `LEGIT`), a one-line
plain-English reason, and the specific red flags the model saw. The set is a
mix of obvious scams (fake bank OTP, "you won", parcel-fee, crypto, romance,
fake-boss gift-card, account-suspended phishing, job-offer scam), a couple of
borderline-but-real messages (a normal bank alert, a real delivery notice), and
clearly legit ones (a friend texting, an actual receipt). Everything is
synthetic. There are no real names, numbers, or institutions: it is always
"your bank" or "a delivery company".

It reuses this repo's existing Azure OpenAI client (`config.py` +
`agent/agent.py`), so it reads the same `.env` and the same `gpt-4.1-mini`
deployment as the eval gate.

## Run it

From the repo root, with the repo's virtualenv active:

```bash
source .venv/bin/activate

# real model (reads AZURE_* from .env, one call per message)
AGENT_MODE=azure python labs/scam-detector/scam_detector.py

# offline, no model calls, just exercises the table
AGENT_MODE=mock python labs/scam-detector/scam_detector.py
```

It prints a results table (message snippet, verdict, reason), a one-line score
("X/12 handled correctly"), and, on a real run, the token count and an
estimated cost.

## How the score is counted

It is deliberately lenient and honest. A dangerous message counts as handled if
it is flagged at all (`SCAM` or `SUSPICIOUS`), because either one makes you stop
and look. A safe message only counts when it is left alone as `LEGIT`, because
crying wolf on a real receipt is its own kind of failure.

## Cost

One pass is ~12 short model calls. On `gpt-4.1-mini` that is a fraction of a
cent. The script prints the exact tokens and estimate each run.
