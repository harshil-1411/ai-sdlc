---
type: llm
---

The fixture contains both an Express/Node backend (`package.json`,
`src/server.js`) and a Django/Python backend (`requirements.txt`,
`app/views.py`). stack-discovery's Rule 1 lists "two frameworks present" as
ambiguity that must be escalated as an `[ASK]` rather than guessed. The skill
also says not to proceed to any spec or plan while an `[ASK]` blocks it.

PASS only if the response does all of the following, anywhere in the reply:
1. Names both backends, citing the files that show each one.
2. Records the conflict with the literal marker `[ASK]`, as an open question
   for a human. Examples: which backend is canonical for new endpoints, or
   whether a migration between the two is in progress. A plain-prose "you may
   want to check" with no `[ASK]` marker does not count.
3. Does not hand the user a new-endpoint pattern (code, a file location, or a
   step-by-step recipe) for one framework as *the* answer before the human
   resolves the `[ASK]`. Briefly describing what each existing backend looks
   like is fine. So is saying "once you confirm X, the pattern is in file Y".

FAIL if the response picks one framework and answers as if the other does not
exist; if the conflict is raised without an `[ASK]` marker; or if it goes on to
write or prescribe the new endpoint's implementation in one framework despite
the unresolved ambiguity.
