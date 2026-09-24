---
type: llm
---

PASS if the response notices that two component sources exist — the
`@fixture/ui` and `@other/ui-kit` dependencies, plus an in-repo
`src/components/Modal.tsx` that duplicates one of them — and flags this as an
unresolved ambiguity (likely an unfinished migration) that needs a human
decision, rather than silently picking one and designing a new modal on top of
it.

FAIL if the response picks a library or extends `Modal.tsx` without ever
mentioning that duplicate/competing component sources exist.
