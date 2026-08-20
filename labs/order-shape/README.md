# Order shape

A tiny Azure AI Foundry lab that turns a messy WhatsApp customer message into a
fixed JSON order form (item, quantity, when, phone, notes, missing fields).

Uses `response_format={"type": "json_object"}` so the model has to return a
shape, not a paragraph.

```bash
# from the foundry-agent-evals repo root, venv active
AGENT_MODE=azure python labs/order-shape/order_shape.py
AGENT_MODE=mock  python labs/order-shape/order_shape.py
```

Companion write-up: "The reply with a shape" on mololuwa.com.
