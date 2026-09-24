---
type: llm
focus: { source: file, path: 'plan/FIX-101.md' }
---

PASS if the committed plan's "Files that change" (or equivalent) names real
paths from the fixture repo — `src/server/routes/auth.ts` and/or
`src/server/auth/mfa.ts` — and extends them rather than inventing a parallel
MFA module, and includes a proof/test-mapping row for REQ-AUTH-01 and
REQ-AUTH-02 from the spec.

FAIL if the plan invents files or modules that don't exist in the fixture
repo without a written justification, or omits a named test for either
requirement, or the file is missing/empty.
