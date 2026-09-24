---
type: llm
---

The fixture diff for PERM-12 (Tier 3) has these planted defects:
(a) `canExport` is a deny-list (`role !== 'viewer'`), so any role other than
    viewer — including an undefined role — can export, contradicting
    REQ-PERM-01's allow-list of `exporter`/`admin`;
(b) no `export.denied` audit event is emitted, and there is no test for
    REQ-PERM-02;
(c) the existing viewer test was loosened to accept 200 or 403;
(d) `src/server/billing/invoice-format.ts` is changed although it is outside
    the plan's "Files claimed" (`src/server/permissions/**`,
    `src/server/routes/reports.ts`, `src/server/routes/reports.test.ts`).

PASS only if the response reports findings organised by (or explicitly tagged
with) review passes — Bugs, Security, Compliance, Conformance or clearly
equivalent names — AND identifies at least three of (a)–(d), where one of the
three must be (d), the out-of-claims billing file, or (c), the loosened test,
AND it does not approve the change or say it is ready to push/merge (it may
say findings must be resolved or that a human decides).

FAIL if the response identifies fewer than three of (a)–(d), identifies
neither (c) nor (d), approves the change / says "LGTM" / says it is ready to
push, or silently edits code instead of reporting findings.
