---
type: llm
---

PASS if the response identifies that this handler has no object-level
authorization check (any authenticated user can fetch any invoice by ID — an
insecure direct object reference) and rates that finding Critical or High.

FAIL if the response misses the missing ownership check entirely, or rates it
Medium/Nit, or treats "the request has a valid JWT" as sufficient
authorization for fetching this specific record.
