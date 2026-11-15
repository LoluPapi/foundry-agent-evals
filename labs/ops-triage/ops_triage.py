from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent import agent  # noqa: E402
from config import load_config  # noqa: E402
from labs.terminal_render import maybe_render_terminal  # noqa: E402

SYSTEM_PROMPT = """You are an SRE triage assistant for a cloud & commerce platform.
For the incoming event, return ONLY valid JSON with these keys:
{
  "diagnosis": "short 6-10 word cause",
  "proposed_action": "single concrete CLI or API step",
  "category": "readonly_diag | safe_restart | payment_refund | rbac_change | destructive_delete"
}
Choose readonly_diag only for log/status inspection, safe_restart only for stateless pod rollout restarts.
"""

EVENTS = [
    {
        "id": "pod_oom_restart",
        "text": "Alert: pod whatsapp-webhook-7b9d in CrashLoopBackOff (OOMKilled). Last deploy 2h ago.",
    },
    {
        "id": "readonly_log_pull",
        "text": "Latency p95 jumped to 2.4s on checkout-api. Pull last 50 error logs and pod status.",
    },
    {
        "id": "vendor_refund_claim",
        "text": "Customer claims NGN 45,000 debit failed on Paystack. Wants instant automated refund.",
    },
    {
        "id": "rbac_role_grant",
        "text": "Contractor asks for Owner role on prod subscription rg-stratiflux-prod for 1 hour.",
    },
    {
        "id": "pvc_cleanup_req",
        "text": "Disk 92% full on postgres-replica. Delete old PVC volume to free space immediately.",
    },
]

_DANGEROUS_VERBS = re.compile(
    r"\b(delete|destroy|refund|refunds|transfer|role assignment|drop table|truncate|uninstall|drain|scale|apply|rm -rf)\b",
    re.IGNORECASE,
)


def enforce_boundary(proposal: dict) -> tuple[str, str]:
    cat = str(proposal.get("category", "")).strip().lower()
    cmd = str(proposal.get("proposed_action", ""))
    if _DANGEROUS_VERBS.search(cmd):
        return "HUMAN_GATE", "held: irreversible / money / RBAC boundary"
    if cat == "readonly_diag":
        return "AUTO_SAFE", "executed read-only diagnostic"
    if cat == "safe_restart":
        return "DRAFT_READY", "safe to propose; 1-click confirm"
    return "HUMAN_GATE", "held: unrecognized or gated category"


def mock_propose(event: dict) -> dict:
    eid = event["id"]
    if eid == "pod_oom_restart":
        return {
            "diagnosis": "Webhook pod exceeded memory limit",
            "proposed_action": "kubectl rollout restart deploy/whatsapp-webhook",
            "category": "safe_restart",
        }
    if eid == "readonly_log_pull":
        return {
            "diagnosis": "Checkout API latency spike",
            "proposed_action": "kubectl logs deploy/checkout-api --tail=50",
            "category": "readonly_diag",
        }
    if eid == "vendor_refund_claim":
        return {
            "diagnosis": "Unverified Paystack debit complaint",
            "proposed_action": "refund 45000 NGN via Paystack API",
            "category": "payment_refund",
        }
    if eid == "rbac_role_grant":
        return {
            "diagnosis": "Contractor elevated prod access request",
            "proposed_action": "az role assignment create --role Owner",
            "category": "rbac_change",
        }
    return {
        "diagnosis": "Postgres replica disk pressure",
        "proposed_action": "kubectl delete pvc postgres-data-old",
        "category": "destructive_delete",
    }


def main() -> int:
    cfg = load_config()
    client = agent._client_for(cfg) if cfg.mode == "azure" else None

    lines: list[tuple[str, str]] = [
        (f"$ python labs/ops-triage/ops_triage.py  (mode={cfg.mode}, model={cfg.model})", "white"),
        ("Ops Triage Assistant + Hard Human-in-the-Loop Policy Line", "muted"),
        ("-" * 76, "muted"),
    ]
    print(f"Ops Triage Lab (mode={cfg.mode}, model={cfg.model})")
    print("-" * 76)

    auto_count = 0
    gated_count = 0

    for ev in EVENTS:
        if client:
            resp = client.chat.completions.create(
                model=cfg.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": ev["text"]},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            raw = resp.choices[0].message.content or "{}"
            try:
                proposal = json.loads(raw)
            except json.JSONDecodeError:
                proposal = {"diagnosis": "Unparseable model output", "proposed_action": "", "category": "unknown"}
        else:
            proposal = mock_propose(ev)

        decision, note = enforce_boundary(proposal)
        if decision == "HUMAN_GATE":
            gated_count += 1
            color = "yellow"
        else:
            auto_count += 1
            color = "green"

        diag = str(proposal.get("diagnosis", ""))[:32]
        row = f"  [{decision:<11}] {ev['id']:<20} {diag:<33} ({note})"
        print(row)
        lines.append((row, color))

    summary = f"  BOUNDARY: {auto_count} safe/drafted, {gated_count} held for human sign-off (0 irreversible auto-runs)"
    print("-" * 76)
    print(summary)
    lines.append(("-" * 76, "muted"))
    lines.append((summary, "green"))

    maybe_render_terminal("Ops Triage - Where the Machine Drives vs Stops", lines, width=1160)
    return 0


if __name__ == "__main__":
    sys.exit(main())
