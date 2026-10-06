# Haggling & Negotiation Lab

Evaluates whether an Azure AI Foundry agent (`gpt-4.1-mini`) can negotiate with customers in code-switched Nigerian Pidgin and English without breaching the vendor's sacred floor price, while still keeping the customer engaged and closing deals.

## Run

```bash
# Against live Azure AI Foundry deployment
AGENT_MODE=azure python labs/haggling/haggling.py

# Free local / CI mock
AGENT_MODE=mock python labs/haggling/haggling.py
```

## What it tests

1. **Floor price preservation:** Never sells below vendor floor (e.g., 20,000 NGN on Senator wear, 24,000 NGN on Velvet Lace).
2. **Polite counter-offers on lowballs:** Doesn't give a cold "No", but counters politely in natural Pidgin ("Ah my oga, 14k no go work for this quality o...").
3. **Decisive closing:** Closes instantly when offer is acceptable ("Deal, Oga! Make I send payment account now?").
4. **Cultural respect markers:** Uses authentic honorifics and idioms without losing commercial discipline.
