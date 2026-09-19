# Intent: Three arXiv-inspired SDLC process improvements

Tracker: PILOT-50   Author: suparn.bector@msbdocs.com, engineering   Date: 2026-09-19   Status: accepted

## Problem
Three gaps in the evidence-sdlc process were identified from research review in an
earlier session and discussed, but never implemented:

1. **No mid-flight checkpoint for long Tier 2/3 work.** A session can run through an
   entire long, high-risk change and only be checked at the bookend gates (plan
   approval at the start, review at the end). Drift, a wrong assumption, or an
   approach that has gone sideways is not caught until the change is already fully
   built, which is the most expensive point to discover it.
2. **Risk-tiering ignores accumulated technical debt.** A change that looks routine
   in isolation can land in a module that is already debt-laden (thin tests, known
   workarounds, prior incidents) and carry materially higher risk than its stated
   tier reflects. `risk-tiering`'s classification questions don't currently ask
   about this.
3. **No eval requirement in a new skill's Definition of Done.** A new skill can ship
   with zero eval coverage — its behavior is undemonstrated until someone happens to
   run one by hand later.

Affected: skill authors working in this plugin repository, and anyone running the
evidence-sdlc process on Tier 2/3 changes in a consuming repository (engineers and
reviewers who rely on risk-tiering output and the skill-authoring Definition of Done).

## Proposed outcome
- Tier 2/3 work that is expected to run long gets an explicit mid-flight checkpoint
  requirement (a defined trigger and what the checkpoint must confirm), not just
  start/end gates.
- `risk-tiering`'s classification step asks about known technical debt in the area
  touched, and debt-laden areas raise the effective tier rather than being silently
  absorbed into a lower one.
- A new skill's Definition of Done includes "at least one eval case exists" as a
  checked item, not an optional afterthought.

Measurable: each of the three shows up as a concrete, checkable step in the relevant
skill's instructions (risk-tiering, skill-creator or an equivalent DoD reference, and
wherever Tier 2/3 process steps are defined) — not just written guidance that nothing
enforces.

## Affected users and systems
- Internal: skill authors (this repo), engineers and reviewers in any repository that
  installs the `evidence-sdlc` plugin.
- Systems: `plugins/evidence-sdlc/skills/risk-tiering/SKILL.md`,
  `plugins/evidence-sdlc/skills/codebase-grounded-planning/SKILL.md` (or wherever
  Tier 2/3 execution steps live), `anthropic-skills:skill-creator` / this repo's own
  skill-authoring Definition of Done reference, and any gate script that should
  enforce these mechanically.

## Regulated record impact
No. These are changes to this framework's own process skills (markdown instructions
and, potentially, a gate script), not to a regulated record. Note: this framework's
skills *govern* how other repositories handle their regulated records, but the
authoring content itself is not one.

## Compliance evidence impact
Unknown / not applicable to evidence-chain's own compliance evidence. Per
`.evidence/context/compliance.md`, evidence-chain's own regulatory posture is
entirely `[ASK]` (open questions 1–5, unresolved). Whether downstream users cite
evidence-chain's own controls in their own audits (compliance.md open question 4) is
unresolved and out of scope here — this intent only changes the framework's internal
process guidance, not any claim evidence-chain makes about itself.

## Data classification
None.

## Constraints
- Additive only: existing intent/spec/plan/DoD workflows already in use must keep
  working unchanged for callers who don't hit the new checkpoint/debt/eval steps.
- No new external dependencies (repo has no package manager — see
  `.evidence/context/stack.md`).
- Bash scripts here are gated as "source" by `gate-plan-exists.sh` (default glob);
  markdown skill files are exempt from that gate. This plan/spec covers both kinds
  of edits.

## Out of scope
- Retroactively adding eval cases to already-shipped skills.
- A general technical-debt tracking system — only wiring an existing/asserted debt
  signal into risk-tiering's classification questions.
- Mid-flight checkpoints for Tier 0/1 work.
- Resolving the open `[ASK]` items in `.evidence/context/compliance.md` — unrelated
  to this change.

## Open questions
None essential to starting design work. If skill-creator's own Definition of Done
reference doesn't live in this repo, confirm with a skill-authoring owner where it
should be added — routed during spec, not blocking intent.
