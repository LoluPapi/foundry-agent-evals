#!/usr/bin/env python
"""Turn a messy WhatsApp customer message into a structured order.

Uses Azure OpenAI JSON mode (response_format=json_object) so the model must
return a fixed shape: item, quantity, date/when, phone, notes, and a
confidence. That is the whole point: a reply with a shape, not a paragraph.

Run:

    AGENT_MODE=azure python labs/order-shape/order_shape.py
    AGENT_MODE=mock  python labs/order-shape/order_shape.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent import agent  # noqa: E402
from config import load_config  # noqa: E402

SYSTEM_PROMPT = (
    "You turn messy customer WhatsApp messages into a clean order form. "
    "Reply with ONLY a JSON object and nothing else, matching this shape:\n"
    '{"item": "<what they want>", "quantity": <number or null>, '
    '"when": "<date or timing or null>", "phone": "<phone or null>", '
    '"notes": "<anything else short>", "missing": ["<fields still unclear>"]}\n'
    "Use null for unknown fields. Put every field you cannot fill into "
    '"missing". Do not invent a price. Do not invent a phone number. Keep '
    "notes under 12 words."
)

# Synthetic messy messages. No real PII.
MESSAGES = [
    {
        "id": "ankara_hold",
        "text": "pls hold d green ankara dress 4 me till friday, i go come pay",
    },
    {
        "id": "asoebi_bulk",
        "text": "i need aso-ebi for my wedding ooo, like 50 guests, blue and gold, "
                "call me on 08012345678 when ready",
    },
    {
        "id": "jollof_200",
        "text": "wedding for 200 pple, jollof + chicken, sat 15th march, abeg confirm",
    },
    {
        "id": "airtime",
        "text": "send 5000 glo airtime to 08054321098 now pls",
    },
    {
        "id": "vague",
        "text": "how much for the dress",
    },
    {
        "id": "electricity",
        "text": "i need 10000 ikeja electric token for meter 12345678901",
    },
]


def _mock_parse(text: str) -> dict:
    low = text.lower()
    if "ankara" in low:
        return {
            "item": "green ankara dress",
            "quantity": 1,
            "when": "friday",
            "phone": None,
            "notes": "hold until friday",
            "missing": ["phone"],
        }
    if "aso-ebi" in low or "aso ebi" in low:
        return {
            "item": "aso-ebi blue and gold",
            "quantity": 50,
            "when": None,
            "phone": "08012345678",
            "notes": "wedding guests",
            "missing": ["when"],
        }
    if "jollof" in low:
        return {
            "item": "jollof and chicken",
            "quantity": 200,
            "when": "saturday 15 march",
            "phone": None,
            "notes": "wedding catering",
            "missing": ["phone"],
        }
    if "airtime" in low:
        return {
            "item": "Glo airtime",
            "quantity": 5000,
            "when": "now",
            "phone": "08054321098",
            "notes": "",
            "missing": [],
        }
    if "token" in low or "meter" in low:
        return {
            "item": "Ikeja electric token",
            "quantity": 10000,
            "when": None,
            "phone": None,
            "notes": "meter 12345678901",
            "missing": ["when", "phone"],
        }
    return {
        "item": "dress",
        "quantity": None,
        "when": None,
        "phone": None,
        "notes": "price inquiry only",
        "missing": ["quantity", "when", "phone", "which dress"],
    }


def _parse(text: str, cfg) -> dict:
    if cfg.mode == "mock":
        return _mock_parse(text)

    client = agent._client_for(cfg)
    resp = client.chat.completions.create(
        model=cfg.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    if resp.usage:
        agent.USAGE["prompt_tokens"] += resp.usage.prompt_tokens
        agent.USAGE["completion_tokens"] += resp.usage.completion_tokens
        agent.USAGE["total_tokens"] += resp.usage.total_tokens
        agent.USAGE["calls"] += 1
    raw = (resp.choices[0].message.content or "").strip()
    return json.loads(raw)


def main() -> int:
    cfg = load_config()
    agent.reset_usage()

    print(f"Order shape  (mode={cfg.mode}, model={cfg.model})")
    print("-" * 72)

    ok = 0
    for m in MESSAGES:
        try:
            out = _parse(m["text"], cfg)
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] {m['id']:<16} {e}")
            continue

        item = str(out.get("item") or "?")[:28]
        qty = out.get("quantity")
        when = str(out.get("when") or "-")[:18]
        missing = out.get("missing") or []
        shaped = isinstance(out, dict) and "item" in out and "missing" in out
        if shaped:
            ok += 1
            tag = "OK"
        else:
            tag = "BAD"
        print(
            f"  [{tag}]  {m['id']:<16} item={item:<28} qty={str(qty):<6} "
            f"when={when:<18} missing={missing}"
        )

    print("-" * 72)
    print(f"  shaped {ok}/{len(MESSAGES)} messages into the order form")
    u = agent.USAGE
    if u["calls"]:
        cost = (
            u["prompt_tokens"] / 1_000_000 * cfg.price_in_per_1m
            + u["completion_tokens"] / 1_000_000 * cfg.price_out_per_1m
        )
        print(
            f"  tokens: {u['total_tokens']} "
            f"({u['prompt_tokens']} in / {u['completion_tokens']} out) "
            f"over {u['calls']} model calls"
        )
        print(
            f"  est. cost this run: ${cost:.4f} "
            f"(at ${cfg.price_in_per_1m}/M in, ${cfg.price_out_per_1m}/M out)"
        )
    else:
        print("  tokens: 0 (mock mode)")
    print()
    return 0 if ok == len(MESSAGES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
