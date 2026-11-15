# Model Upgrade Regression Diff Lab

Runs the same English, Nigerian Pidgin, and strict payment-safety cases side by
side against two live Azure deployments (`gpt-4.1-mini` vs `gpt-5.4-mini`) to
catch silent quality or latency regressions before flipping production traffic.

In `AGENT_MODE=mock`, the candidate model intentionally simulates a Pidgin
haggling floor regression on `yoruba_pidgin_split` so you can see the gate exit `1`
and print `BLOCK upgrade`.

```bash
AGENT_MODE=mock python labs/regression-diff/regression_diff.py
AGENT_MODE=azure python labs/regression-diff/regression_diff.py
```
