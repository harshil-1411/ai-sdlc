---
type: llm
---

PASS if the response proposes moving slower checks (full e2e, extended
security) to a later stage (PR, merge, or nightly) while keeping the commit
stage fast, and explicitly separates what should **block** (compilation, unit/
integration failure, critical/high security findings) from what should
**inform** (style nits, non-critical findings) rather than treating everything
as equally blocking.

FAIL if the response proposes running the full suite (including full e2e and
all security scans) on every commit/push, or does not distinguish blocking
checks from advisory ones.
