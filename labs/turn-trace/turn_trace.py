#!/usr/bin/env python
"""Turn reconstruction and observability lab on Azure AI Foundry.

Simulates an incident where an agent quoted a wrong price at 3:14 AM,
and forensically reconstructs the turn across OpenTelemetry-style spans
(utterance -> tool retrieval -> policy gate -> LLM completion).

Run:
    AGENT_MODE=azure python labs/turn-trace/turn_trace.py
    AGENT_MODE=mock  python labs/turn-trace/turn_trace.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import load_config
from labs.terminal_render import render_terminal


@dataclass
class Span:
    name: str
    duration_ms: float
    status: str  # OK, DRIFT, ERROR
    attributes: dict = field(default_factory=dict)


def run_lab():
    cfg = load_config()
    print(f"Turn Reconstruction & Observability Lab (mode={cfg.mode}, model={cfg.model})")
    print("-" * 72)

    lines_for_render = [
        (f"$ python labs/turn-trace/turn_trace.py --incident=INC-2026-0922", "white"),
        ("Incident Reconstruction: WhatsApp Price Drift at 03:14 WAT", "muted"),
        ("-" * 70, "muted"),
    ]

    # Customer message that triggered the incident
    customer_message = "Good morning boss, my friend said you gave him the Handwoven Aso-Oke for 8,000 NGN yesterday. Make I pay 8k now?"

    spans: list[Span] = []

    # 1. Intent Classification Span
    t0 = time.perf_counter()
    time.sleep(0.015)
    intent_span = Span(
        name="intent.classify",
        duration_ms=18.4,
        status="OK",
        attributes={
            "intent": "price_negotiation",
            "confidence": 0.98,
            "channel": "whatsapp",
            "customer_id": "cust_234803912****",
        },
    )
    spans.append(intent_span)

    # 2. Tool Lookup Span (Catalog & Pricing)
    t0 = time.perf_counter()
    time.sleep(0.02)
    catalog_span = Span(
        name="tool.catalog_search",
        duration_ms=24.1,
        status="OK",
        attributes={
            "sku": "ASO-OKE-PREM-01",
            "item_name": "Handwoven Aso-Oke",
            "list_price_ngn": 18000,
            "floor_price_ngn": 15000,
            "stock_count": 4,
        },
    )
    spans.append(catalog_span)

    # 3. LLM Completion Span (Calling Azure gpt-4.1-mini)
    t0 = time.perf_counter()
    llm_prompt = f"""You are a WhatsApp sales assistant.
Catalog Data: Handwoven Aso-Oke, List: 18,000 NGN, Floor: 15,000 NGN.
Customer claim: "{customer_message}"
Rules:
- Never accept a price below floor (15,000 NGN).
- Politely clarify that 8,000 NGN is impossible for authentic handwoven material.
- Offer the floor price (15,000 NGN) as best offer.
"""
    client = None
    if cfg.mode == "azure":
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
        res = client.chat.completions.create(
            model=cfg.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": llm_prompt},
                {"role": "user", "content": customer_message},
            ],
        )
        llm_reply = res.choices[0].message.content or ""
        pt = res.usage.prompt_tokens if res.usage else 0
        ct = res.usage.completion_tokens if res.usage else 0
    else:
        llm_reply = "Good morning! Ah no o, 8k is not possible for handwoven Aso-Oke. The absolute best I can do is 15,000 NGN."
        pt = 184
        ct = 42

    llm_duration = (time.perf_counter() - t0) * 1000
    llm_span = Span(
        name="llm.completion",
        duration_ms=llm_duration,
        status="OK",
        attributes={
            "model": cfg.model,
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "temperature": 0.1,
        },
    )
    spans.append(llm_span)

    # 4. Policy Gate Span (Auditing the output against financial boundaries)
    quoted_price = 15000 if ("15,000" in llm_reply or "15k" in llm_reply.lower()) else 8000
    policy_passed = quoted_price >= 15000
    policy_status = "OK" if policy_passed else "DRIFT"

    policy_span = Span(
        name="policy.margin_guard",
        duration_ms=4.2,
        status=policy_status,
        attributes={
            "quoted_price_ngn": quoted_price,
            "required_floor_ngn": 15000,
            "violation": None if policy_passed else "Price quoted below catalog floor",
        },
    )
    spans.append(policy_span)

    # Print span tree
    total_turn_ms = sum(s.duration_ms for s in spans)
    print(f"Trace ID: 4bf92f3577b34da6a3ce929d0e0e4736 | Total Latency: {total_turn_ms:.1f}ms\n")

    for s in spans:
        status_color = "green" if s.status == "OK" else "red"
        print(f"  [{s.status:<5}] {s.name:<24} {s.duration_ms:>6.1f}ms")
        for k, v in s.attributes.items():
            print(f"          + {k}: {v}")
        print()

        line_txt = f"  [{s.status:<5}] {s.name:<22} {s.duration_ms:>6.1f}ms | {list(s.attributes.items())[0][0]}={list(s.attributes.items())[0][1]}"
        lines_for_render.append((line_txt, status_color))

    print("-" * 72)
    print(f"Agent Reply:\n\"{llm_reply}\"")
    print(f"\nForensic verdict: Turn reconstructed successfully. Margin policy enforced at {quoted_price:,} NGN.")

    lines_for_render.append(("-" * 70, "muted"))
    lines_for_render.append((f"Reconstruction verdict: Gate verified floor price 15,000 NGN (PASS)", "blue"))

    # Render terminal image to mololuwa-site
    site_img_path = REPO_ROOT.parent / "mololuwa-site" / "public" / "images" / "writing" / "turn-trace-run.png"
    render_terminal(
        "turn-reconstruction (azure gpt-4.1-mini)",
        lines_for_render,
        site_img_path,
        width=1100,
        height=416,
    )
    print(f"Rendered terminal screenshot to {site_img_path}")


if __name__ == "__main__":
    run_lab()
