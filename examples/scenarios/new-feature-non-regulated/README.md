# Scenario: a new user story, non-regulated product

**Who this is for:** a small SaaS team with no regulatory obligation, shipping a
normal user-facing feature. This is the lightest path through the framework — most
teams' most common case — and it's worth reading first for that reason.

## The story

> "As an account admin, I want to export my team's usage data as a CSV, so I can
> analyse it in our own spreadsheet."

This repo already has `.evidence/context/` established (`stack-discovery` ran once,
`compliance-discovery` recorded "none apply, confirmed by [name], [date]" — a real,
recorded answer, not silence).

## Walkthrough

**1 · Plan.** `intent-capture` writes `intent.md`:
- Problem: admins currently email support for a data pull.
- Regulated record impact: No — usage data, not a signed or approved record.
- Data classification: internal analytics data, no PII beyond what the admin already
  sees in the product.

**Risk tier, stated immediately after:** `risk-tiering` marks this **Tier 1 —
Routine**. Non-regulated, not a new production endpoint most users will call in
volume, fully coverable by existing tests. One line, in the intent: *"Tier 1 — new
export path, no regulated record, existing auth model reused."*

**2 · Design.** At Tier 1, `spec.md` is **not required** — the Definition of Ready
only asks for a stated problem, a stated acceptance criterion, and a plan on disk.
This team writes one anyway, short, because the export format has a few edge cases
worth deciding on paper (empty team, >10k rows, unicode in team names) — `spec-and-
design` still applies UX-checklist thinking to those states even without the full
regulatory-control-table ceremony a Tier 2/3 spec would carry.

**3 · Build.** `codebase-grounded-planning` runs in plan mode: `codebase-cartographer`
finds the existing `/api/export/*` pattern and the CSV-writing helper the product
already has for a different report — the plan **extends** that helper rather than
writing a new one. `plan.md` is committed (required at every tier); `gate-plan-exists`
would otherwise deny the first `Edit`.

**4 · Test.** `test-strategy` names the layer: an integration test hitting the new
endpoint with 0, 1, and >10k rows, plus a unicode-team-name case. One test per
acceptance criterion — Tier 1's bar, not Tier 3's full layered suite.

**5 · Deploy.** A normal PR. `require-issue-key` blocks any commit without the tracker
key; `block-protected-branch-push` means the branch goes through a PR, a human code
owner approves, `production-gate` blocks the actual deploy step until a release
authorisation is set.

**6 · Maintain.** `evidence export --write` adds one row to
`validation/traceability.csv`: the requirement, the test that proves it, the commit,
`PASS`, Tier 1, `revalidation: none`. Nothing extra — Tier 1 evidence is meant to be
this small.

## What this scenario deliberately skips

No `regulatory-controls` pass (nothing applies). No `decision-council` (nothing here
is a one-way door). No `secure-api-review` beyond the standard auth-reuse check
(no new trust boundary, no new endpoint class). This is the point: **ceremony scales
with risk**, and this story genuinely doesn't carry much.

## Read next

- [`risk-tiering`](../../../plugins/evidence-sdlc/skills/risk-tiering/SKILL.md) — the
  tier table this scenario cites
- [`codebase-grounded-planning`](../../../plugins/evidence-sdlc/skills/codebase-grounded-planning/SKILL.md)
- [Scenario: a regulated change](../regulated-change-tier3/README.md) — the same six
  stages, all the ceremony this one skipped
