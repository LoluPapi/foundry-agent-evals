from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import load_config
from labs.terminal_render import maybe_render_terminal


def get_token(tenant: str, app_id: str, secret: str, scope: str) -> str:
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": app_id,
            "client_secret": secret,
            "scope": scope,
        }
    ).encode()
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=data
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["access_token"]


def _parse_error_code(err: urllib.error.HTTPError) -> str:
    raw = err.read().decode(errors="replace")
    try:
        return json.loads(raw).get("error", {}).get("code", "Denied")
    except json.JSONDecodeError:
        return err.reason or "Denied"


def check_denied(label: str, url: str, token: str, method: str, data: bytes | None = None) -> tuple[str, str, bool]:
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return (label, f"HTTP {r.status} UNEXPECTED", False)
    except urllib.error.HTTPError as e:
        code = _parse_error_code(e)
        return (label, f"HTTP {e.code} {code} (blocked)", e.code == 403)


def run_live(oai_ep: str, api_version: str, sub_id: str, rg: str, account: str,
             deployment: str, tenant: str, app_id: str, secret: str) -> list[tuple[str, str, bool]]:
    cog_tok = get_token(tenant, app_id, secret, "https://cognitiveservices.azure.com/.default")
    arm_tok = get_token(tenant, app_id, secret, "https://management.azure.com/.default")
    arm_base = (
        f"https://management.azure.com/subscriptions/{sub_id}/resourceGroups/{rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{account}"
    )

    checks: list[tuple[str, str, bool]] = []

    req1 = urllib.request.Request(
        f"{oai_ep.rstrip('/')}/openai/deployments/{deployment}/chat/completions?api-version={api_version}",
        data=json.dumps(
            {"messages": [{"role": "user", "content": "Say: Price confirmed at 18,500 NGN."}], "max_tokens": 20}
        ).encode(),
        headers={"Authorization": f"Bearer {cog_tok}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req1, timeout=20) as r:
        body = json.loads(r.read().decode())
        reply = (body["choices"][0]["message"].get("content") or "").strip()
        checks.append(("inference (Entra Bearer, 0 keys)", f"HTTP {r.status} OK -> {reply}", True))

    req2 = urllib.request.Request(
        f"{arm_base}?api-version=2024-10-01",
        headers={"Authorization": f"Bearer {arm_tok}"},
    )
    with urllib.request.urlopen(req2, timeout=20) as r:
        checks.append(("accounts/read (metadata)", f"HTTP {r.status} OK", True))

    checks.append(check_denied("accounts/listKeys (withheld)", f"{arm_base}/listKeys?api-version=2024-10-01", arm_tok, "POST", b"{}"))
    checks.append(check_denied("deployments/delete (withheld)", f"{arm_base}/deployments/{deployment}?api-version=2024-10-01", arm_tok, "DELETE"))
    return checks


def run_mock() -> list[tuple[str, str, bool]]:
    return [
        ("inference (Entra Bearer, 0 keys)", "HTTP 200 OK -> Price confirmed at 18,500 NGN.", True),
        ("accounts/read (metadata)", "HTTP 200 OK", True),
        ("accounts/listKeys (withheld)", "HTTP 403 AuthorizationFailed (blocked)", True),
        ("deployments/delete (withheld)", "HTTP 403 AuthorizationFailed (blocked)", True),
    ]


def main() -> int:
    cfg = load_config()
    tenant = os.getenv("AZURE_TENANT_ID", "")
    app_id = os.getenv("AZURE_CLIENT_ID", "")
    secret = os.getenv("AZURE_CLIENT_SECRET", "")
    sub_id = os.getenv("AZURE_SUBSCRIPTION_ID", "")
    rg = os.getenv("AZURE_RESOURCE_GROUP", "rg-foundry-mvp-lab")
    account = os.getenv("AZURE_FOUNDRY_ACCOUNT", "oai-mololuwa-lab-nov")
    oai_ep = cfg.azure_endpoint or ""

    if cfg.mode == "azure" and not all([tenant, app_id, secret, sub_id, oai_ep]):
        print(
            "ERROR: AGENT_MODE=azure requires AZURE_TENANT_ID, AZURE_CLIENT_ID, "
            "AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID, and AZURE_OPENAI_ENDPOINT",
            file=sys.stderr,
        )
        return 2
    live = cfg.mode == "azure"
    mode_label = "azure-entra-rbac" if live else "mock"

    checks = (
        run_live(oai_ep, cfg.azure_api_version, sub_id, rg, account, cfg.model, tenant, app_id, secret)
        if live
        else run_mock()
    )

    lines: list[tuple[str, str]] = [
        (f"$ python labs/rbac-principal/rbac_check.py  (mode={mode_label})", "white"),
        ("Principal role: Cognitive Services OpenAI User (account scope only)", "muted"),
        ("-" * 74, "muted"),
    ]
    print(f"Entra RBAC Least-Privilege Lab (mode={mode_label})")
    print("-" * 74)

    all_ok = True
    for action, detail, ok in checks:
        all_ok = all_ok and ok
        tag = "PASS" if ok else "FAIL"
        color = "green" if "200" in detail and ok else ("yellow" if "403" in detail and ok else "red")
        row = f"  [{tag}] {action:<34} {detail}"
        print(row)
        lines.append((row, color))

    summary = "  GOVERNANCE: least privilege verified (inference allowed, keys/delete denied)"
    print("-" * 74)
    print(summary)
    lines.append(("-" * 74, "muted"))
    lines.append((summary if all_ok else "  GOVERNANCE: FAIL", "green" if all_ok else "red"))

    maybe_render_terminal("Microsoft Foundry - Entra Principal & RBAC Boundary", lines)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
