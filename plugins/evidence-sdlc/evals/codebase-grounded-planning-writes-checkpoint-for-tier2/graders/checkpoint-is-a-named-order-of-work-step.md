---
type: llm
focus: { source: file, path: 'plan/EXP-9.md' }
---

This spec is Risk tier: 2, which per codebase-grounded-planning requires a
mid-flight checkpoint: one step in "Order of work" marked `CHECKPOINT`, at
which the agent is meant to stop and re-confirm work against spec.md before
continuing.

PASS if the committed plan's "Order of work" section names one of its
numbered steps as a `CHECKPOINT` step (not just the word appearing somewhere
incidentally), and the plan's "Files that change" / design reuses
`src/server/routes/reports.ts` and `src/server/export/csv.ts`'s `toCsv`
helper rather than inventing a new CSV serializer, and includes a proof/test
row for REQ-EXPORT-01 and REQ-EXPORT-02.

FAIL if there is no explicit `CHECKPOINT` step in "Order of work", if the
plan invents a parallel CSV serializer without justification, or if either
requirement has no named test.
