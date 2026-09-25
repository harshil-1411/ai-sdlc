# Intent: Make the local layer advisory in practice

Tracker: PILOT-62   Author: Suparn Bector (maintainer), drafted by Claude from the PILOT-58 dogfooding findings   Date: 2026-09-25   Status: draft

## Problem
Since 2.1.0 (PILOT-58), the authority for what merges is the base-branch `verify-range` job plus code-owner review (ADR-0004). The local hooks are documented as early feedback. In practice, though, the local layer still costs a human round trip for events that are not the agent's doing, or that the monitor has already undone:

- **Restored violations block.** When a command changes a control-plane file, the integrity monitor restores it from the signed snapshot (`integrity.check`). The violation is still recorded `open`. Push and PRs (`evidence_policy._review_gate`) and source edits (`check_write`, the `serious` list) stay blocked until a human runs `evidence change clear-violations` in their own terminal, while the agent is idle.
- **Human and Claude Code edits are charged to the agent.** The hook runs before Claude Code's permission prompt, so writes by the human or by Claude Code land in the middle of a tool call:
  - `.claude/settings.local.json`: since B4, a pure `permissions.allow` addition is kept, but any other change (a rule removed through `/permissions`, an added directory) is restored and recorded;
  - `managed-settings.json` and `evidence-policy.json`, edited by the human with `sudo` during a call, are recorded as `hidden-change` (two such clears on 2026-09-25, recorded in `ea2f856`);
  - `~/.claude.json` is rewritten by Claude Code itself for bookkeeping, and every such write is a `hidden-change`.
- **Tier 3 needs an org-policy loosening for `acceptEdits` and `auto`.** `check_write` denies Tier 3 source edits in those modes (`deny_tier3_auto_modes`). On this machine the owner had to create `/Library/Application Support/ClaudeCode/evidence-policy.json` to work at all. That per-change local review duplicates what `verify-range` and code-owner review already enforce on the server.

The owner's words (2026-09-25): the friction is "digressing from the purpose".

## Proposed outcome
Owner decisions of 2026-09-25:
1. A violation the monitor has already restored does not block push or source edits, and needs no manual `clear-violations`.
2. Human or Claude Code edits to user control-plane configuration during a tool call are not charged to the agent. This covers `.claude/settings.local.json` beyond permission grants, `managed-settings.json`, `evidence-policy.json` and `~/.claude.json`.
3. Tier 3 is allowed in `acceptEdits` and `auto` once `verify-range` is a required check, without an org-policy loosening.

**Measure:**
- zero human `clear-violations` for restored events or config edits in the next change after this one ships;
- Tier 3 work in `auto` mode on this repository with no org-policy change to the permission-mode keys;
- every agent-caused violation that is not restored still blocks, each with a test.

## Affected users and systems
- The gate engine: integrity monitor, commit/push/edit gates, the `verify-range` CLI and the policy.
- Every repository that runs the plugins, including msb_clm.
- Maintainers and approvers, who carry the round trips today.

## Regulated record impact
Yes. This changes when violation records are open or closed, and adds a new closed-at-birth state. The records stay signed, and every event stays in the audit log. Nothing for end customers.

## Compliance evidence impact
Yes. `governance/control-mapping.md` and `SECURITY.md` describe violations as blocking until a human clears them. Those claims are restated. No regulatory framework is established for this repository (`.evidence/context/compliance.md`: all `[ASK]`).

## Data classification
None. The signing key is a secret that must never be read or exposed, and no change may read it.

## Constraints
- **No weakening of what merges.** `verify-range` (ADR-0004) stays authoritative and unchanged in its rules 0–3. Rule 5 is only tightened.
- **Every new tolerance comes with a negative test.** An agent-caused violation that is not restored still blocks, and a config write that runs commands (hooks, MCP servers, a status line) is still restored.
- **Tier 3 process:** plan approval by a second human (Harshil); review agents run one at a time; no edits during a review.
- **Backwards compatible:** 2.1.x violation records, snapshots and audit logs still verify.

## Out of scope
- Automating the release record in CI on merge (see spec, "Out of scope").
- Concurrency and signed-record acceptance mid-call (PILOT-59).
- Approve, clear (for violations that are not restored), release and merge stay human-only.

## Open questions
- Is `evidence-policy.json` on this machine root-owned (created with `sudo`)? The design treats a system config file as not agent-writable only when it is not owned by, or writable by, the session's user. Owner: maintainer, `ls -l "/Library/Application Support/ClaudeCode/"`.
- Is `approval.github_repo` set in the org policy? Gate detection needs a pinned repository. Owner: maintainer.
