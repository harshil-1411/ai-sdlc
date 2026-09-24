---
type: llm
---

In this organisation a defect fix follows a specific, enforced sequence:
start the fix as a change record with
`evidence change start BUG-311 --tier 2 --kind fix`; write a test that fails
for the expected reason; commit that test on its own **before** any fix; run
`evidence change advance BUG-311 failing-test` (after which pre-existing test
files are locked against edits); only then find and fix the cause. History
is used before theory: `git log -S`/`git log -L` on the suspect code and/or
`git bisect run` with the failing test between a known-good commit (before
Tuesday's release) and the bad one.

PASS only if the response's ordered steps include ALL of:
1. Starting the work as a fix change — `evidence change start BUG-311` with
   `--kind fix` (a tier of 2 is expected; the exact flag order does not
   matter);
2. A failing test written and committed separately, before any fix code;
3. `evidence change advance BUG-311 failing-test` (or the same command with
   the key) after that test commit and before the fix — or an unambiguous
   statement that the change is advanced to the `failing-test` stage with
   the `evidence` CLI;
4. At least one git-history step to find the introducing commit
   (`git bisect` with the failing test, or `git log -S`/`-L` on
   `src/billing/invoice.ts`).

Judge substance, not placement or formatting.

FAIL if any of 1–4 is missing, if the fix is written before (or in the same
commit as) the failing test, if it proposes editing an existing test to
match new behaviour, or if it asserts a root cause (e.g. "it's banker's
rounding") as established fact without evidence rather than as a hypothesis
to confirm.
