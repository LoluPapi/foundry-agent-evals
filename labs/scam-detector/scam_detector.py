#!/usr/bin/env python
"""A tiny scam / phishing text-message detector.

Reuses the repo's Azure OpenAI client setup (config.py + agent/agent.py) and
asks the model to read ~12 short, synthetic text messages and label each one
SCAM, SUSPICIOUS, or LEGIT with a one-line reason and the red flags it saw.

Run it:

    AGENT_MODE=azure python labs/scam-detector/scam_detector.py   # real model
    AGENT_MODE=mock  python labs/scam-detector/scam_detector.py   # offline

It prints a results table and a one-line summary, mirroring run_evals.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the repo root importable so we can reuse the existing client + config.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent import agent  # noqa: E402
from config import load_config  # noqa: E402

# The classifier persona. Kept short to keep tokens (and cost) low.
SYSTEM_PROMPT = (
    "You read everyday text messages and decide whether each one is a scam or "
    "phishing attempt. For the single message you are given, reply with ONLY a "
    "compact JSON object and nothing else:\n"
    '{"verdict": "SCAM|SUSPICIOUS|LEGIT", "reason": "<one short plain sentence>", '
    '"red_flags": ["<short flag>", ...]}\n'
    "SCAM = clearly malicious (it wants money, codes, logins, or to move you off "
    "to a shady link). SUSPICIOUS = some red flags but it could plausibly be "
    "real. LEGIT = a normal, safe message. Keep the reason under 15 words and "
    "list at most three red flags (empty list if none)."
)

# Synthetic messages. No real people, numbers, or institution names: it is
# always "your bank" or "a delivery company". `expect` is what a careful human
# would say, used only for the summary line.
MESSAGES = [
    {
        "text": "Your bank: a payment of $450 is pending. If this wasn't you, "
                "reply with the 6-digit code we just texted to cancel it.",
        "expect": "SCAM",
        "note": "fake bank OTP",
    },
    {
        "text": "CONGRATULATIONS! Your number was picked in our promo and you "
                "have won $5,000. Claim now: hxxp://claim-now.xyz/win",
        "expect": "SCAM",
        "note": "you won",
    },
    {
        "text": "A delivery company: your parcel is held at our depot. A small "
                "customs fee of $1.99 is due. Pay here: hxxp://parcel-fee.co/pay",
        "expect": "SCAM",
        "note": "parcel delivery fee",
    },
    {
        "text": "Hi! I made 312% on a crypto platform this week. I can show you "
                "how, just DM me and I'll send the signup link to get started.",
        "expect": "SCAM",
        "note": "crypto returns",
    },
    {
        "text": "I feel such a connection with you. I'm stuck offshore and my "
                "card is blocked. Could you send a little to help me get home? "
                "I'll pay you back, promise.",
        "expect": "SCAM",
        "note": "romance",
    },
    {
        "text": "Hi, it's the boss. I'm in a meeting and need you to buy 5 gift "
                "cards for a client right now. Send me the codes, I'll reimburse "
                "you after.",
        "expect": "SCAM",
        "note": "fake boss gift-card",
    },
    {
        "text": "Your account has been suspended due to unusual activity. Verify "
                "your identity within 24 hours or it will be closed: "
                "hxxp://secure-verify.co/login",
        "expect": "SCAM",
        "note": "account suspended phishing",
    },
    {
        "text": "We reviewed your profile and want to offer you a remote job at "
                "$35/hr, no interview needed. Send your bank details to set up "
                "payroll today.",
        "expect": "SCAM",
        "note": "job offer scam",
    },
    {
        "text": "Your bank: a debit of $52.30 to a grocery store was made on the "
                "card ending 1234. If this was you, no action is needed.",
        "expect": "LEGIT",
        "note": "real-sounding bank alert (borderline)",
    },
    {
        "text": "A delivery company: your order is out for delivery today and "
                "should arrive between 2 and 6 PM. No reply needed.",
        "expect": "LEGIT",
        "note": "real delivery notice (borderline)",
    },
    {
        "text": "hey! are we still on for lunch saturday? lmk what time works "
                "for you",
        "expect": "LEGIT",
        "note": "a friend texting",
    },
    {
        "text": "Thanks for your purchase. Your receipt total is $14.20 and a "
                "copy is in your account. No action needed.",
        "expect": "LEGIT",
        "note": "an actual receipt",
    },
]


def _parse(raw: str) -> dict:
    """Pull the JSON object out of the model reply, tolerating stray text."""
    text = raw.strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"verdict": "?", "reason": "could not parse model reply",
                "red_flags": []}
    verdict = str(data.get("verdict", "?")).upper().strip()
    if verdict not in {"SCAM", "SUSPICIOUS", "LEGIT"}:
        verdict = "?"
    return {
        "verdict": verdict,
        "reason": str(data.get("reason", "")).strip(),
        "red_flags": data.get("red_flags", []) or [],
    }


def classify(message: str, cfg) -> dict:
    """One model call per message. Mock mode returns a canned LEGIT reply."""
    if cfg.mode == "mock":
        return {"verdict": "LEGIT", "reason": "mock mode: no model was called",
                "red_flags": []}
    raw = agent._complete(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": message}],
        model=cfg.model, cfg=cfg, temperature=0.0,
    )
    return _parse(raw)


def _is_correct(expect: str, verdict: str) -> bool:
    """A lenient, honest score.

    A dangerous message is "handled" if it is flagged at all (SCAM or
    SUSPICIOUS), since either one makes the reader stop and look. A safe
    message is only "handled" when it is left alone as LEGIT, because crying
    wolf on a real receipt is its own kind of failure.
    """
    if expect == "SCAM":
        return verdict in {"SCAM", "SUSPICIOUS"}
    return verdict == "LEGIT"


def _snippet(text: str, width: int = 44) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= width else one_line[: width - 1] + "\u2026"


def main() -> int:
    cfg = load_config()
    agent.reset_usage()

    rows = [(m, classify(m["text"], cfg)) for m in MESSAGES]

    print(f"\nScam detector  (mode={cfg.mode}, model={cfg.model})")
    print("-" * 78)
    print(f"  {'message':<45}{'verdict':<12}{'reason'}")
    print("-" * 78)
    correct = 0
    for m, r in rows:
        if _is_correct(m["expect"], r["verdict"]):
            correct += 1
        print(f"  {_snippet(m['text']):<45}{r['verdict']:<12}{r['reason']}")
    print("-" * 78)

    total = len(rows)
    print(f"  {correct}/{total} handled correctly "
          "(scams flagged, safe messages left alone)")

    if cfg.mode != "mock":
        u = agent.USAGE
        est_cost = (
            u["prompt_tokens"] / 1_000_000 * cfg.price_in_per_1m
            + u["completion_tokens"] / 1_000_000 * cfg.price_out_per_1m
        )
        print(f"  tokens: {u['total_tokens']} "
              f"({u['prompt_tokens']} in / {u['completion_tokens']} out) "
              f"over {u['calls']} model calls")
        print(f"  est. cost this run: ${est_cost:.4f} "
              f"(at ${cfg.price_in_per_1m}/M in, ${cfg.price_out_per_1m}/M out)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
