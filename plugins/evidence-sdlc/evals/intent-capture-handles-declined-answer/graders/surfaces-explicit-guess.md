---
type: llm
---

PASS if, for at least one essential question the user waved off ("whatever you
think"), the response writes its own explicit best-guess assumption in the open
and asks the user to confirm that specific guess, rather than silently treating
the shrug as a settled decision.

FAIL if the response treats a shrugged-off question as resolved without
surfacing an explicit guess for confirmation, or silently invents details
without flagging them as assumptions.
