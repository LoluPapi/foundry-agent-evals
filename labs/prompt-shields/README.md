# Prompt Shields Lab

Tests Azure AI Content Safety Prompt Shields (`text:shieldPrompt?api-version=2024-09-01`)
against clean Nigerian commerce messages, direct user jailbreaks, and indirect prompt
injections hidden inside supplier invoices and bank transfer PDFs.

Demonstrates why two walls matter: Prompt Shields (Wall 1) stops explicit document overrides
and hidden HTML/PDF comments before the model sees them, while a deterministic policy guard
(Wall 2) catches subtle bracketed notes that slip past the classifier.

```bash
AGENT_MODE=mock python labs/prompt-shields/prompt_shields.py
AGENT_MODE=azure CONTENT_SAFETY_ENDPOINT=... CONTENT_SAFETY_KEY=... python labs/prompt-shields/prompt_shields.py
```
