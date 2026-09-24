---
type: llm
---

PASS if the response notices that both an Express/Node backend
(`package.json`, `src/server.js`) and a Django/Python backend
(`requirements.txt`, `app/views.py`) are present, treats this as a genuine
ambiguity (e.g. an in-progress migration or an unresolved split) and escalates
it as an open question (`[ASK]`) to a human rather than silently picking one
framework to answer with.

FAIL if the response picks one framework and answers as if the other doesn't
exist, or otherwise fails to surface the conflict as something a human needs
to resolve.
