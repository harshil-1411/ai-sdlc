# Spec: Three arXiv-inspired SDLC process improvements
Tracker: PILOT-50   From: intent/2026-09-19-arxiv-inspired-sdlc-improvements/intent.md   Risk tier: 3

Risk classification: Tier 3 — per `risk-tiering`, "any change to this framework's own
gates." This spec touches `risk-tiering/SKILL.md` itself, `codebase-grounded-planning`'s
execution guidance, the tiered Definition of Done template, and (for enforcement)
`template-sensor.sh`, an existing advisory PostToolUse hook.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Requirements

| ID | Requirement | Source (intent.md section) | Acceptance |
| --- | --- | --- | --- |
| REQ-DEBT-01 | `risk-tiering/SKILL.md`'s Tiers section gains an explicit technical-debt classification question, asked alongside the existing tier-trigger questions. | Proposed outcome, item 2 | SKILL.md contains a named question about accumulated debt in the touched area, placed before "When in doubt, tier up." |
| REQ-DEBT-02 | The debt question names concrete, already-available evidence signals to check (known-issues/workaround references, prior-incident references, thin test coverage) rather than requiring a new artifact or tool. | Constraints — additive only, no new dependency | Signals are things `codebase-cartographer` or a grep can already find; no new file format or register is mandated. |
| REQ-DEBT-03 | A debt-laden area raises the effective tier by one notch (never lowers it, never exceeds Tier 3). | Proposed outcome, item 2 | SKILL.md states the direction (raise only) and the ceiling explicitly. |
| REQ-CKPT-01 | `codebase-grounded-planning`'s `plan.md` template gains a "Mid-flight checkpoint" field that is required for Tier 2/3 work and marked N/A for Tier 1. | Proposed outcome, item 1 | `templates/plan.md` has the new field; Tier 1 may write "N/A." |
| REQ-CKPT-02 | The checkpoint names its trigger point as an explicit marker inside the plan's "Order of work" steps (not a wall-clock or session-count heuristic), and states what must be reconfirmed against `spec.md` at that point. | Proposed outcome, item 1; Rejected alternatives | `codebase-grounded-planning/SKILL.md`'s "While implementing" section instructs stopping at the marked step to re-validate scope/assumptions before continuing, and recording drift if found. |
| REQ-CKPT-03 | `template-sensor.sh` gains an advisory (never-deny) check: a Tier 2/3 `plan.md` with no checkpoint marker in "Order of work" produces an advisory note, the same way it already flags a stub "Areas of concern." | Proposed outcome, item 1 ("checkable, not just guidance") | Extending the existing sensor rather than adding a new gate script; sensor continues to exit 0 always. |
| REQ-EVAL-01 | The tiered Definition of Done template gains a line, scoped to "a new skill is introduced," requiring at least one eval case under the plugin's `evals/` directory before the skill is Done. | Proposed outcome, item 3 | `templates/definition-of-ready-and-done.md` references the existing `evals/README.md` convention (case.yaml + prompt.md + graders/), not a new mechanism. |
| REQ-EVAL-02 | `template-sensor.sh` gains an advisory check: a new `SKILL.md` written under `plugins/*/skills/*/` with no sibling case directory under the plugin's `evals/` produces an advisory note. | Proposed outcome, item 3 | Advisory only, consistent with the sensor's existing never-deny behaviour; does not block skill authoring mid-session. |

## Design
Modules touched (all already exist — this is additive editing, not new components):
- `plugins/evidence-sdlc/skills/risk-tiering/SKILL.md` — add the debt question (REQ-DEBT-01..03).
- `plugins/evidence-sdlc/skills/codebase-grounded-planning/SKILL.md` — add checkpoint
  instruction to "While implementing" (REQ-CKPT-02).
- `plugins/evidence-sdlc/templates/plan.md` — add "Mid-flight checkpoint" field (REQ-CKPT-01).
- `plugins/evidence-sdlc/templates/definition-of-ready-and-done.md` — add eval-case DoD
  line for new skills (REQ-EVAL-01).
- `plugins/evidence-sdlc/scripts/template-sensor.sh` — extend with two more advisory
  checks (REQ-CKPT-03, REQ-EVAL-02), following the exact pattern already used for the
  stub "Areas of concern" check: read the tool input, check a condition, print an
  advisory `hookSpecificOutput` with no `permissionDecision` (never deny), exit 0.

No new file formats, no new gate script, no new external dependency
(`codebase-cartographer` survey confirmed the repo has no package manager and this
change adds none). The eval mechanism (`case.yaml`/`prompt.md`/`graders/`, invoked via
`claude plugin eval`) already exists and is adopted across all five plugins — REQ-EVAL-01
points at it rather than inventing a parallel one.

## Regulatory control impact
`.evidence/context/compliance.md` has no framework confirmed as applicable — every row
is `[ASK]`, unresolved (open questions 1–5). This spec does not resolve those; per
intent's "Out of scope," they are unrelated to this change. No framework's control set
is loaded here because none has been confirmed as applicable to this repository.

| Framework | Control ID | Applies? | How it is satisfied | Evidence |
| --- | --- | --- | --- | --- |
| — none confirmed applicable | — | N/A | This change edits the framework's own internal process documentation and an advisory hook script; it is not itself a regulated record, and no framework has been confirmed to apply to evidence-chain's own repository (see compliance.md). | `.evidence/context/compliance.md` |

## Evidence impact
No existing requirement entries, traceability rows, or evidence deliverables in a
*consuming* repository are affected — this change only edits evidence-chain's own
skill/template/hook content. Out of regulatory scope because this repository is the
framework itself, not a product under validation (per `.evidence/context/compliance.md`
and `stack.md`). Within this repo, the change modifies the guidance three future
changes will be judged against (risk tier, plan.md shape, and skill-authoring DoD) —
existing intent/spec/plan artifacts already on disk are not retroactively altered.

## Diagrams
None of the five inclusion conditions apply: no service or system boundary is added,
no ordering/approval/retry flow is introduced, no record moves through states, no
sensitive data moves, and no infrastructure changes. All diagram headings omitted.

## Security design
No new trust boundary, endpoint, tenancy scoping, egress, or dependency. The one
security-adjacent property worth stating explicitly: `template-sensor.sh` is a
PostToolUse advisory sensor that today always exits 0 (never denies). REQ-CKPT-03 and
REQ-EVAL-02 must preserve that — they add advisory notices, not new deny paths. If
either were implemented as a hard deny instead, it would silently promote an advisory
sensor into a gate with no fail-open/closed policy decision behind it, which is exactly
the kind of change `risk-tiering` says must never happen by accident. This is called
out again under Areas of concern.

## UX
Not applicable — no UI. Table omitted per template instruction (delete rows that do
not apply); there is no end-user-facing surface to this change at all, including no
CLI flag or prompt behaviour change beyond the advisory hook's printed message text.

Component reuse: reuses the existing advisory-sensor pattern in `template-sensor.sh`
(stub-detection for "Areas of concern") rather than introducing a new hook or gate
script; reuses the existing `evals/` case convention rather than inventing a new eval
mechanism; reuses the existing tiered-table format in
`definition-of-ready-and-done.md` rather than a new DoD document.

## Areas of concern
1. **Debt signal has no dedicated register.** `toolchain.md` confirms this repo has no
   test-management tool, no CI, and no issue tracker of its own. REQ-DEBT-02 therefore
   asks about heuristic signals (documented workarounds, prior incidents, thin
   coverage) rather than a queryable source of truth. Whether a lightweight
   `debt-register.md` convention should exist later is a real, unresolved question —
   explicitly out of scope per intent.md, routed to: whoever owns `risk-tiering`
   (maintainer, unnamed — see toolchain.md open question 3, no maintainer role is
   named anywhere in this repo yet).
2. **Advisory-vs-gate boundary must not drift.** `template-sensor.sh` is documented as
   always exiting 0. Extending it (REQ-CKPT-03, REQ-EVAL-02) carries a real risk that a
   future edit turns an advisory note into a deny without anyone deciding that on
   purpose. Routed to: whoever reviews the `template-sensor.sh` diff (named reviewer
   requirement below) — explicitly confirm the exit-0 behaviour is preserved before
   approving.
3. **skill-creator's own Definition of Done is outside this repo.** `docs/extending.md`
   documents this repo's own skill-authoring conventions, but the generic
   `anthropic-skills:skill-creator` skill referenced in the session's skill list is not
   a file in this repository — this spec can only add the eval-case requirement to
   *this* repo's own `definition-of-ready-and-done.md` and `docs/extending.md`, not to
   skill-creator itself. Routed to: Anthropic skill-creator maintainers (not
   resolvable from inside this repo) — flagged, not solved.
4. **Checkpoint relies on agent self-discipline, not a technical control.**
   REQ-CKPT-02's checkpoint is enforced by the executing agent choosing to stop and
   re-validate at the marked step; nothing in Claude Code today gives a hook visibility
   into "50% of plan.md steps done." REQ-CKPT-03's sensor can only check that the
   marker *exists in the text* of plan.md, not that the agent actually paused there.
   Routed to: whoever owns `codebase-grounded-planning` — reconsider if this is
   sufficient once/if Claude Code exposes step-level progress to hooks.

## Rejected alternatives
- **Checkpoint trigger — wall-clock or session-boundary based, instead of a plan.md
  marker.** Rejected: Claude Code sessions compact/summarize transparently, so
  "elapsed time" or "new session" is not a reliable proxy for "long," and neither is
  auditable after the fact from plan.md alone. A checkpoint step named explicitly in
  "Order of work" is visible to a reviewer reading plan.md and consistent with the
  skill's existing "re-read plan.md before each step" discipline
  (`codebase-grounded-planning/SKILL.md`, "While implementing"). Review trigger: revisit
  if Claude Code ever exposes session/turn-count telemetry to hooks (see Areas of
  concern #4) — a technical signal would be strictly better than a text marker.
- **Debt signal — a new mandatory `debt-register.md` file repo-wide.** Rejected as
  over-scope: intent.md's "Out of scope" explicitly limits this change to "wiring an
  existing/asserted debt signal into risk-tiering's classification," not building a new
  tracking system. Heuristic signals were chosen instead, consistent with how
  `risk-tiering` already asks evidence-gathering questions elsewhere in the skill
  rather than mandating new artifacts. Review trigger: revisit if a consuming repo's
  own discovery process (`stack-discovery`, `toolchain-discovery`) starts surfacing a
  debt-register convention as commonly already present — then risk-tiering could point
  at it instead of asking free-form.
