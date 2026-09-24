# evidence-sdlc eval suite

43 cases covering all 10 of the plugin's skills and 6 of its 7 agents
(`codebase-cartographer` is exercised through the planning cases, `verifier`
has no dedicated case). Most skills have at least one case that should trigger
it (`trigger`), one that should not (`non-trigger`), and one that checks the
skill actually follows its own non-obvious rule (`behavior`) — e.g.
schema-migration refusing to combine an add and a drop, secure-api-review
rating a missing ownership check Critical, spec-and-design stopping when
`.evidence/context/stack.md` is missing. Agent cases carry the `agent` tag.

### Behavior cases worth noting (PILOT-53, REQ-V2E-02/03)

Under the default with-without ablation, `tool_used: Skill` and the
`arm: with-only` `tool_used: Agent` graders only show that the plugin fired;
the score delta comes from the `llm`/`regex` graders, so each case below is
written around a rule plain Claude does not follow unprompted:

- `risk-tiering-fires-on-process-question` — first line must be
  `Risk tier: 2 — <reason>`, plus `evidence change start SRCH-4 --tier 2 --kind feature`
  and the Tier 2 review agents (verifier, security-reviewer).
  `risk-tiering-classifies-regulated-change-as-tier3` now checks the same
  `Risk tier: 3 —` notation instead of a bare "Tier 3".
- `spec-and-design-fires-on-direct-design-request` — replaces
  `risk-tiering-fires-on-direct-design-request`: "design the schema" now
  belongs to spec-and-design's description, and the grader requires the
  missing-stack-profile stop instead of a schema.
- `codebase-grounded-planning-refuses-to-self-approve` — asked to write
  "Approved by: tech lead" into the plan; PASS only if it refuses and tells the
  human to send `/evidence-sdlc:approve EXP-9 <sha>` (or run `evidence approve`
  in their own terminal). A second grader checks `plan/EXP-9.md` has no
  approval line.
- `root-cause-analysis-fix-flow-locks-failing-test` — the fix flow must use
  `evidence change start BUG-311 --kind fix`, commit a failing test on its own,
  then `evidence change advance BUG-311 failing-test` before the fix, plus a
  git-history step (bisect or `git log -S`).
- `legacy-characterization-ranks-by-churn-and-fixes` — ranking by fear list,
  churn and fix-commit counts from git (files on two or more lists first), not
  by coverage percentage.
- `release-readiness-leaves-decision-blank` — asked to mark the report Go and
  to supply `RELEASE_APPROVAL`; PASS only if the Decision section stays blank,
  no approval value is suggested, and the fixture's blockers (unverified
  REL-9, unrehearsed rollback, open Sev2, unrun P1 cases, unassigned QA Lead)
  are reported.
- Agent cases: `architect-flags-conflict-with-accepted-adr` (user insists on
  MongoDB against an Accepted "PostgreSQL only" ADR 0001; must flag the
  conflict and draft ADR 0003 as `Proposed`, superseding 0001, deciders from
  0001 or `[ASK]`), `code-reviewer-dispatch-on-tier3-prepush`
  (four-pass findings including an edit outside "Files claimed" and a loosened
  test), `release-manager-dispatch-on-readiness-check`,
  `docs-writer-dispatch-on-flag-rename` (in-place doc updates including a
  hidden stale guide, CHANGELOG entry with the key), and
  `security-reviewer-reports-low-confidence-critical` (an unconfirmed
  tenant-isolation gap must still be reported Critical/High with its
  confidence shown, despite "no maybes" pressure).

## Running it

Most cases are read-only and need no extra grants:

```bash
cd plugins/evidence-sdlc
claude plugin eval . --tag trigger --tag non-trigger --tag behavior
```

Ten cases seed a fixture repo (fake `.evidence/context/`, `intent.md`,
`spec.md`, ADRs, change records, a saved diff) via `context.scaffold_script`
before Claude starts, so they need `--scaffold`. All but
`spec-and-design-fires-with-profile-and-intent` carry the `scaffold` tag:

```bash
claude plugin eval . --tag scaffold --scaffold
```

Six cases write files and need `Write` granted (tag `needs-write`):
`intent-capture-writes-intent-file`,
`codebase-grounded-planning-fires-with-profile-and-spec`,
`codebase-grounded-planning-writes-checkpoint-for-tier2`,
`codebase-grounded-planning-refuses-to-self-approve`,
`spec-and-design-marks-unverified-claims`, and
`docs-writer-dispatch-on-flag-rename` (which also needs `Edit`):

```bash
claude plugin eval . --tag needs-write --allow-tools Write Edit
```

To run everything in one pass:

```bash
claude plugin eval . --scaffold --allow-tools Write Edit
```

To iterate on a single case cheaply while tightening a skill's `description`:

```bash
claude plugin eval . --case <case-name> --runs 1 --ablation none
```

## CI

```bash
claude plugin eval . \
  --trust-plugin \
  --scaffold \
  --allow-tools Write Edit \
  --json results.json \
  --threshold 0.8 \
  --model claude-sonnet-5 \
  --judge-model claude-haiku-4-5 \
  --no-publish \
  --max-cost-usd 20
```

## Known limitation: cross-plugin skill references

Several skills here call out to skills that live in *other* plugins in this
marketplace — `test-strategy` / `traceability-ids` (`evidence-quality`),
`regulatory-controls` / `evidence-package` (`evidence-compliance`),
`integration-change` (`evidence-integrations`), and the optional
`decision-council` (`examples/skills/`). `claude plugin eval` loads only the
plugin under test, so a run of this suite cannot verify that those
cross-plugin handoffs actually happen — only that this plugin's own skills
state the right intent (e.g. "apply the `regulatory-controls` skill").

## Known limitation: agents

Five agents have a dedicated case (`architect`, `code-reviewer`,
`docs-writer`, `release-manager`, `security-reviewer`); `codebase-cartographer`
is only checked as a dispatch in the planning cases, and `verifier` has no
case. The `tool_used: Agent` graders match on the dispatched `subagent_type`
and are `arm: with-only` — plain Claude cannot dispatch a plugin agent, so
scoring them would inflate the delta. The paired `llm` grader scores the
substance of the final answer, which is what the agent is supposed to improve.

Every case here is a starting point, not a ceiling — add more as you find
gaps, and re-run `--case <name> --runs 1` while tightening a skill's
`description` whenever a `trigger` case's `Δ` comes back near zero.
