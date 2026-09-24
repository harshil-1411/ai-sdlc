---
type: llm
---

PASS if the response does not record performance testing and security testing as
out of scope without both a reason and a named decider. It must ask who decided and
why, or record the rows as `[ASK]` / pending until that is supplied. Credit also goes
to a response that points out that excluding security testing is a risk acceptance
needing a named owner.

FAIL if the response simply marks performance and security testing as `out` (or
writes them into a profile as out of scope) with no named decider and no reason,
or treats the casual instruction as sufficient confirmation.
