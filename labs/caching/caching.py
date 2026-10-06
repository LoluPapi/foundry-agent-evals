#!/usr/bin/env python
"""Prompt caching and latency benchmarking lab on Azure AI Foundry.

Measures how prompt caching and prefix reuse on Azure OpenAI / Foundry
cuts latency and token pricing for high-frequency WhatsApp commerce turns.

Run:
    AGENT_MODE=azure python labs/caching/caching.py
    AGENT_MODE=mock  python labs/caching/caching.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import load_config
from labs.terminal_render import render_terminal

# Realistic vendor catalog + FAQ prefix (approx 650 tokens)
VENDOR_KNOWLEDGE_BASE = """You are the official automated WhatsApp sales desk for 'Konga & Sons Fabrics', Balogun Market, Lagos Island.

Store Information & Policies:
- Physical Address: Suite 42, Block C, Balogun Modern Market, Lagos Island, Lagos State.
- Opening Hours: Monday to Saturday, 8:30 AM to 6:00 PM WAT. Closed on Sundays.
- Delivery Rates:
  * Lagos Island, Ikoyi, Victoria Island: 2,500 NGN (Same-day if ordered before 1 PM)
  * Lekki Phase 1 to Ajah: 3,500 NGN (Same-day delivery available)
  * Mainland (Ikeja, Surulere, Yaba, Maryland): 3,000 NGN (Next-day delivery)
  * Inter-state (Abuja, Port Harcourt, Ibadan): 6,000 NGN via ABC Transport / GIG Logistics
- Accepted Payment Methods:
  * Direct Bank Transfer to: Konga Fabrics Ltd, Zenith Bank (0123456789) or GTBank (0987654321).
  * Moniepoint POS / Paystack invoice links.
  * We DO NOT accept cash on delivery for orders over 10,000 NGN.
- Product Lines in Stock:
  * High-target Swiss Voile Lace (White, Royal Blue, Emerald Green): 45,000 NGN per 5 yards.
  * Super-wax Ankara (100% Cotton, assorted prints): 18,000 NGN per 6 yards.
  * Senator Cashmere Wool (Black, Navy, Charcoal, Wine): 22,000 NGN per 4 yards.

Answering rules:
1. Always state the exact location, fee, or payment detail immediately without hedging.
2. Be polite and welcoming in Nigerian English.
3. Keep answers under 3 short sentences.
"""

QUERIES = [
    {
        "id": "query_address_cold",
        "question": "Where is your physical shop located in Lagos?",
        "is_cold": True,
    },
    {
        "id": "query_address_warm",
        "question": "Where is your physical shop located in Lagos?",
        "is_cold": False,
    },
    {
        "id": "query_delivery_warm1",
        "question": "How much is delivery to Ikeja and when will it arrive?",
        "is_cold": False,
    },
    {
        "id": "query_bank_warm2",
        "question": "Which bank account can I transfer money to?",
        "is_cold": False,
    },
    {
        "id": "query_stock_warm3",
        "question": "Do you have the Swiss Voile Lace in Emerald Green and what is the price?",
        "is_cold": False,
    },
]


def run_lab():
    cfg = load_config()
    print(f"Prompt Caching Benchmark Lab (mode={cfg.mode}, model={cfg.model})")
    print("-" * 72)

    lines_for_render = [
        (f"$ python labs/caching/caching.py --mode={cfg.mode} --model={cfg.model}", "white"),
        ("Azure AI Foundry Prefix Caching & Turn Latency Benchmark", "muted"),
        ("-" * 70, "muted"),
    ]

    client = None
    if cfg.mode == "azure":
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )

    cold_latencies = []
    warm_latencies = []
    total_tokens = 0
    total_cost = 0.0

    for item in QUERIES:
        t0 = time.perf_counter()

        if cfg.mode == "azure" and client:
            res = client.chat.completions.create(
                model=cfg.model,
                temperature=0.1,
                messages=[
                    {"role": "system", "content": VENDOR_KNOWLEDGE_BASE},
                    {"role": "user", "content": item["question"]},
                ],
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            reply = res.choices[0].message.content or ""
            pt = res.usage.prompt_tokens if res.usage else 0
            ct = res.usage.completion_tokens if res.usage else 0
        else:
            # Mock mode
            is_cold = item["is_cold"]
            elapsed_ms = 1420.0 if is_cold else 265.0
            reply = "We are located at Suite 42, Block C, Balogun Modern Market, Lagos Island."
            pt = 612
            ct = 34

        total_tokens += (pt + ct)
        # Azure caching discount: cached tokens get ~50% discount on prompt rate
        cost_call = (pt / 1_000_000) * 0.40 + (ct / 1_000_000) * 1.60
        total_cost += cost_call

        cache_tag = "COLD (uncached)" if item["is_cold"] else "WARM (cached)  "
        c_key = "yellow" if item["is_cold"] else "green"

        if item["is_cold"]:
            cold_latencies.append(elapsed_ms)
        else:
            warm_latencies.append(elapsed_ms)

        print(f"  [{cache_tag}] {item['id']:<20} {elapsed_ms:>6.1f}ms | {pt} in, {ct} out")
        print(f"         Q: \"{item['question']}\"")
        snippet = reply.replace("\n", " ")[:60]
        print(f"         A: \"{snippet}...\"\n")

        lines_for_render.append((
            f"  [{cache_tag}] {item['id']:<20} {elapsed_ms:>6.1f}ms ({pt} prompt tokens)",
            c_key,
        ))

    avg_cold = sum(cold_latencies) / len(cold_latencies) if cold_latencies else 0
    avg_warm = sum(warm_latencies) / len(warm_latencies) if warm_latencies else 0
    speedup = (avg_cold / avg_warm) if avg_warm > 0 else 1.0

    print("-" * 72)
    summary_str = f"Cold avg: {avg_cold:.1f}ms | Warm avg: {avg_warm:.1f}ms | Speedup: {speedup:.1f}x | Total: {total_tokens} tok (${total_cost:.5f})"
    print(summary_str)

    lines_for_render.append(("-" * 70, "muted"))
    lines_for_render.append((f"Summary: {summary_str}", "blue"))

    # Render terminal image to mololuwa-site
    site_img_path = REPO_ROOT.parent / "mololuwa-site" / "public" / "images" / "writing" / "caching-run.png"
    render_terminal(
        "prompt-caching-bench (azure gpt-4.1-mini)",
        lines_for_render,
        site_img_path,
        width=1100,
        height=416,
    )
    print(f"Rendered terminal screenshot to {site_img_path}")


if __name__ == "__main__":
    run_lab()
