# Entra Principal & Least-Privilege RBAC Lab

Verifies least-privilege access for a Foundry agent identity without static API keys:

1. Acquires a Microsoft Entra Bearer token and completes inference (`HTTP 200`).
2. Reads account metadata (`HTTP 200`).
3. Attempts `listKeys` and `deployments/delete` and proves Azure blocks both with
   `HTTP 403 AuthorizationFailed`.

```bash
AGENT_MODE=mock python labs/rbac-principal/rbac_check.py
AGENT_MODE=azure AZURE_TENANT_ID=... AZURE_CLIENT_ID=... AZURE_CLIENT_SECRET=... \
  AZURE_SUBSCRIPTION_ID=... AZURE_OPENAI_ENDPOINT=... python labs/rbac-principal/rbac_check.py
```
