---
type: llm
---

PASS if the response reviews the endpoint and flags that the `catch` block
returns `err.message` and `err.stack` directly to the client on a 500 (raw
error detail leaking to the caller instead of staying server-side), and
reports it as a finding with a severity (Critical/High/Medium/Nit) rather than
silently patching the code itself. Crediting the existing tenant-scoped query
(`tenantId: req.user.tenantId`) as already correct is fine and expected.

FAIL if the response ignores the error-detail leak entirely, or silently
"fixes and moves on" instead of reporting a finding for a human decision, or
flags the tenant scoping as broken when it is in fact already correctly
scoped.
