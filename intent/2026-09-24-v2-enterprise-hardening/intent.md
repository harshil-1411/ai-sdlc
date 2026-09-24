# Intent: v2 enterprise hardening — close every finding in the v1 enterprise audit

Tracker: PILOT-53   Author: suparn.bector@msbdocs.com, engineering   Date: 2026-09-24   Status: accepted

## Problem
The v1 enterprise audit (2026-09-24, https://claude.ai/artifact/2AC3mxyFdmkHKYgogwLFpG)
scored the framework 2.1/5 and recommended against making it an organisation standard.
The audit combined a full code read, direct probes of the gate scripts, and three live
headless scenario runs. It found that the central promise ("the controls run at the
moment the agent acts") does not hold up:

- **The gates can be bypassed.** Shell writes skip the plan gate, and any `plan.md`
  anywhere unlocks every edit. Absolute paths under `/tmp/` or `/docs/` are exempt.
  The push gate checks only the local branch name. The production gate is a
  case-sensitive word list that also blocks harmless commands. Malformed input
  fails open.
- **Approvals and tier rules are self-attested.** In a live run the agent wrote its
  own "Approved" line on a Tier 3 plan and then implemented the change.
- **Nobody can answer "who approved it" or "which agent changed it".** The audit
  log can be edited and is never committed. The CLI cannot see approvals, the agent
  that made a change, or whether a test actually ran.
- **The lifecycle has no state, so stages get skipped.** Across three runs, intent,
  risk tiering, spec, test strategy and both review agents never ran, and nothing
  noticed.
- **It assumes a single repository.** There is no organisation policy layer and no
  scoping for monorepos.
- **The governance documents overclaim.** They describe enforcement that does not
  exist.
- **Product gaps.** The CLI is not shipped in any plugin. There are no versions,
  no slash commands, no CI, and the install path is a placeholder. Eval results are
  not retained, and many eval cases do not beat the no-plugin baseline.

## Proposed outcome
Every v1 finding is either fixed in this repository and verified, or explicitly
listed as an owner action with the mechanism already shipped (for example, server-side
branch protection, which a plugin cannot set). The audit is then re-run independently
and the results published as a v1-vs-v2 comparison.

Measurable:
- Every probe in the v1 security table is encoded as a regression test that now passes.
- The three v1 scenarios, re-run, show the lifecycle stages enforced.
- A full 3-run baselined eval pass completes, with the summary committed.
- An independent re-audit produces the v2 score.

## Affected users and systems
All five plugins, the CLI, governance documents, managed-settings template, docs,
and every adopting repository.

## Regulated record impact
No. The framework itself is not a regulated record. The changes strengthen the controls
adopters rely on for theirs.

## Compliance evidence impact
Governance documents are corrected so they no longer claim more than the mechanisms
deliver. New SOC 2 / ISO 27001 / NIST SSDF mapping points only at real mechanisms.

## Data classification
None. The secret scanner handles secrets transiently and never logs matched values.

## Constraints
- Additive where possible. Existing adopters' `plan.md` layouts keep working.
- Python 3 (standard library only) may replace `jq` as the gate engine's runtime.
  The engine fails closed if Python is missing, as it previously did for `jq`.
- The engine denies nothing in a repository without the framework installed.
- Do not break this repository's own development loop.

## Out of scope
- Anything requiring the maintainer's accounts: creating a git remote, publishing
  to a marketplace, configuring server-side branch protection, enabling OTel
  collection. The mechanisms and setup docs ship; the actions are listed as owner actions.
- Mobile-native test automation (unchanged from PILOT-51).

## Open questions
None blocking. Maintainer decisions recorded 2026-09-24:
- Work on branch `hardening/v2`.
- Move personal files out of the repo.
- Verification budget up to $80.
- Use the work email as owner.
