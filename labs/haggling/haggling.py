#!/usr/bin/env python
"""Haggling and negotiation lab for WhatsApp commerce agents on Azure AI Foundry.

Evaluates how well a sales agent negotiates in code-switched Nigerian Pidgin and
English without breaching the vendor's floor price, losing the deal, or flatly
shutting down the customer.

Run:
    AGENT_MODE=azure python labs/haggling/haggling.py
    AGENT_MODE=mock  python labs/haggling/haggling.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent import agent
from config import load_config
from labs.terminal_render import render_terminal

HAGGLING_SYSTEM_PROMPT = """You are a sharp, warm WhatsApp sales assistant for an authentic Nigerian fashion vendor (Oga Clothier).
You sell Senator wear (List price: 25,000 NGN, absolute floor price: 20,000 NGN) and Velvet Lace (List price: 30,000 NGN, floor: 24,000 NGN).

Rules for haggling:
1. Floor price is SACRED. Never agree to sell below the floor price under any circumstances (Senator floor is 20,000 NGN per piece, Velvet Lace floor is 24,000 NGN per piece).
2. If customer offers below floor, do NOT say flat "No" or "I cannot help". Counter-offer politely with the floor price or offer a bundle (e.g. "Ah my oga, 15k no go work for this quality o, but I fit do 20k last for you if you take am today").
3. If customer's offer is at or above the floor price (for example 40k for two senators, or 21k for one), ACCEPT decisively and move to payment ("Deal! 40k for the two is fine. Make I send account details now?").
4. Always match the customer's language: speak natural Nigerian Pidgin and English with respect markers (Oga, Chief, Madam).
5. Never hedge. Answer with concrete numbers and immediate next step.
"""

CASES = [
    {
        "id": "lowball_senator",
        "item": "Senator wear",
        "list": 25000,
        "floor": 20000,
        "customer": "Abeg chief, last price for the navy blue senator? I get 14k cash now now.",
        "expect_reject_below_floor": True,
        "expect_counter": True,
    },
    {
        "id": "acceptable_senator",
        "item": "Senator wear",
        "list": 25000,
        "floor": 20000,
        "customer": "Oga, 21k for the senator wear make I pay now?",
        "expect_accept": True,
    },
    {
        "id": "extreme_lowball",
        "item": "Velvet Lace",
        "list": 30000,
        "floor": 24000,
        "customer": "I go give you 10k for that velvet lace. Take am or leave am.",
        "expect_reject_below_floor": True,
        "expect_counter": True,
    },
    {
        "id": "bundle_haggle",
        "item": "Senator wear",
        "list": 25000,
        "floor": 20000,
        "customer": "If I pick two senator materials, you fit do 40k total?",
        "expect_accept": True,
    },
    {
        "id": "polite_inquiry",
        "item": "Velvet Lace",
        "list": 30000,
        "floor": 24000,
        "customer": "Good morning boss, what is the best last price for the velvet lace?",
        "expect_counter": True,
    },
]


def evaluate_reply(case: dict, reply: str) -> tuple[bool, str]:
    low = reply.lower()
    floor = case["floor"]

    # Check if agent breached floor price
    # e.g., agreeing to 14k or 10k
    if case.get("expect_reject_below_floor"):
        if "14k" in low or "14,000" in low or "10k" in low or "10,000" in low:
            if "deal" in low or "agreed" in low or "bring" in low or "send account" in low:
                return False, "Breached floor price by accepting lowball"
        # Must counter or state acceptable price
        if not any(token in low for token in ["20k", "20,000", "24k", "24,000", "last", "quality"]):
            return False, "Refused but failed to counter with reasonable price"
        return True, "Defended floor price and offered polite counter"

    if case.get("expect_accept"):
        # Should accept and ask for payment or confirm
        if any(token in low for token in ["deal", "pay", "account", "send", "fine", "pack", "done"]):
            return True, "Accepted valid offer at/above floor and advanced sale"
        return False, "Failed to close on an acceptable offer"

    if case.get("expect_counter"):
        if any(token in low for token in ["24k", "25k", "last", "give you", "do for you"]):
            return True, "Offered best price without breaching floor"
        return False, "Vague response to price inquiry"

    return True, "Handled turn"


def run_lab():
    cfg = load_config()
    print(f"Haggling & Negotiation Lab (mode={cfg.mode}, model={cfg.model})")
    print("-" * 72)

    results = []
    lines_for_render = [
        (f"$ python labs/haggling/haggling.py --mode={cfg.mode} --model={cfg.model}", "white"),
        ("Haggling & Negotiation Lab: Code-switched Pidgin commerce", "muted"),
        ("-" * 70, "muted"),
    ]

    total_prompt_tok = 0
    total_comp_tok = 0
    start_time = time.time()

    client = None
    if cfg.mode == "azure":
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )

    for case in CASES:
        if cfg.mode == "azure" and client:
            res = client.chat.completions.create(
                model=cfg.model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": HAGGLING_SYSTEM_PROMPT},
                    {"role": "user", "content": case["customer"]},
                ],
            )
            reply = res.choices[0].message.content or ""
            total_prompt_tok += res.usage.prompt_tokens if res.usage else 0
            total_comp_tok += res.usage.completion_tokens if res.usage else 0
        else:
            # Mock mode
            if case.get("expect_reject_below_floor"):
                reply = f"Ah my oga, that price no go work for this pure quality o! But because of you, I fit do {case['floor']:,} last last. Make I pack am?"
            elif case.get("expect_accept"):
                reply = "Sharp deal my boss! That price work well. Make I send you payment account now?"
            else:
                reply = f"Good morning chief! List na {case['list']:,}, but I fit give you {case['floor']:,} last. How you see am?"
            total_prompt_tok += 120
            total_comp_tok += 35

        passed, reason = evaluate_reply(case, reply)
        results.append((case["id"], passed, reason, reply))

        status_tag = "[PASS]" if passed else "[FAIL]"
        print(f"  {status_tag} {case['id']:<18} {reason}")
        print(f"         Customer: \"{case['customer']}\"")
        snippet = reply.replace("\n", " ")[:65]
        print(f"         Agent:    \"{snippet}...\"\n")

        c_key = "green" if passed else "red"
        lines_for_render.append((f"  {status_tag} {case['id']:<18} {reason}", c_key))
        lines_for_render.append((f"         \"{snippet}...\"", "muted"))

    duration = time.time() - start_time
    total_tokens = total_prompt_tok + total_comp_tok
    cost = (total_prompt_tok / 1_000_000) * 0.40 + (total_comp_tok / 1_000_000) * 1.60

    summary_line = f"Pass rate: {sum(1 for r in results if r[1])}/{len(results)} | Tokens: {total_tokens} | Cost: ${cost:.5f}"
    print("-" * 72)
    print(summary_line)
    lines_for_render.append(("-" * 70, "muted"))
    lines_for_render.append((f"Result: {summary_line}", "blue"))

    # Render image to mololuwa-site
    site_img_path = REPO_ROOT.parent / "mololuwa-site" / "public" / "images" / "writing" / "haggling-run.png"
    render_terminal(
        "haggling-lab (azure gpt-4.1-mini)",
        lines_for_render,
        site_img_path,
        width=1100,
        height=430,
    )
    print(f"Rendered terminal screenshot to {site_img_path}")


if __name__ == "__main__":
    run_lab()
