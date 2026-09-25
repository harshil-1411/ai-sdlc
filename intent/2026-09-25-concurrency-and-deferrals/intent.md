# Intent: Make the integrity monitor correct under concurrent tool calls, and close the PILOT-58 review deferrals

Tracker: PILOT-59   Author: Suparn Bector (maintainer), drafted by Claude from CHANGELOG 2.1.0 "Known issues", the PILOT-58 records and the PILOT-62 spec   Date: 2026-09-25   Status: draft

## Problem
Each item below was checked against the code at `7759c17` (origin/main) on 2026-09-25. Where it was reproduced, the reproduction ran the real hook (`hook.py pre|post`) in a scratch repository built with the engine-test helpers (`make_repo`, `start_change`, `run_hook`).

### Concurrency (the core of this change)
The monitor brackets each allowed Bash call with a snapshot (`integrity.snapshot`, in `hook.run_pre`) and a comparison (`integrity.check`, in `hook.run_integrity`). It diffs the **whole** working tree and control plane, so anything written inside a call's window is charged to that call. With parallel subagents, a second session in the same folder, or a human acting mid-call, this is wrong in three ways. All three were reproduced:

- **Another call's work is charged to this call.** Call A (`sleep 5`) and call B (an unparsed `./build.sh`) overlap. B writes the Tier-3-floor file `src/auth/login.py`. B's post records the `tier-floor` violation. A's post then records the same write again, charged to A's session. It also records B's freshly written `violations.json` as a `control-plane` change made by A.
- **A newer, real record is erased (signed mode).** In the same scenario with a signing key, A's post *removes* the `violations.json` that B's post created ("was created by that command and has been removed"). B's entry, with B's session, is gone, and A's re-recording carries A's session. This is the 2026-09-24 data loss that ADR-0001 describes.
- **A human's signed action mid-call is reverted.** The human clears violations (a signed `write_violations`) while call C runs. C's post restores `violations.json` from C's pre snapshot. The open count goes from 0 back to 3: the two old entries, plus a new `control-plane` entry. PILOT-62's spec hands this problem to PILOT-59 ("Accepting validly signed record changes mid-call … belongs to PILOT-59"). The agent workflow notes say "Human `clear-violations` must run while the agent is idle."

ADR-0001 (signature-validated records plus an unsigned lease in `.git/`) was **rejected** in the PILOT-58 security design review:
- signatures bind no path, change or sequence, so an older signed record can be replayed;
- the lease was unsigned;
- losing the lease, or its expiry, skipped judgement.

The rejection asks for a redesign with **attested engine writes, a signed lease and chained snapshots**. The PILOT-58 spec's scope table adds **background writes, pre/post pairing and hook-before-prompt**.

### Monitor gaps deferred from the PILOT-58 security review (commit `faf8bea`)
- **A4, no pre-call audit entry.** `run_pre` writes an audit entry only for a deny or an agent dispatch. A call whose post never runs (interrupted, or its post entry lost) leaves no trace.
- **B1, FIFOs and device links stall hashing.** `integrity._dirty` walks untracked directories with `os.walk` and hashes every name with `_hash` → `st.sha256_file`, which opens with a blocking `open()`. It was reproduced with a FIFO, and separately with a symlink to `/dev/zero`, in an untracked directory: `_dirty` did not return until a 4-second alarm interrupted it. `_hash` catches `OSError`, so only a non-`OSError` alarm ends it. In the hook, the 25-second watchdog ends it, and every Bash call is then denied (pre) or recorded as `integrity-timeout` (post). The walk also follows a symlinked collapsed directory (`os.path.isdir` followed by `os.walk(full)`).
- **B2, the snapshot root isn't compared.** `snapshot` stores `"root"`, but `check` never reads it (confirmed by grep). The post computes `ctx.root` from the post payload's `cwd`. So a command that `cd`s into another repository is compared against the wrong tree.
- **B3, snapshots are world-readable.** They were measured as `$TMPDIR/evidence-chain-snapshots` 0755, the session directory 0755 and the snapshot file 0644 (`st._dir_fd` creates directories 0755 and `st.write_file` creates files 0644). Snapshots hold base64 copies of control-plane files. Nothing checks who owns a directory that already exists in a shared `/tmp`.
- **Nits 2–5** of the same review were deferred without being written down [NEEDS VERIFICATION: their text is in no committed file; owner to supply].
- **`file_in_commit`-style fail-open sweeps** (HANDOFF "Open work"): helpers that return a permissive value when git fails.

### Other deferrals
- **The `cmdparse` newline and heredoc bug** is wider than the CHANGELOG says. `_tokenize` uses `shlex` with `whitespace_split`, which turns every newline into whitespace, so `"\n"` in `CONTROL_OPS` is never produced. `_strip_heredocs` also throws away the rest of the heredoc's operator line. Reproduced through the hook's PreToolUse (all **allowed**):
  - `echo hi⏎touch src/auth/login.py`, parsed as one `echo` command (the same `touch` alone is denied `tier-floor`);
  - `cat <<EOF | sh⏎touch src/auth/login.py⏎EOF`: `| sh` disappears, so the body is not seen as executed;
  - `cat <<EOF && touch src/auth/login.py⏎…`: `&& touch …` disappears.

  The monitor records such writes after the fact, but the pre-check is blind. This is a pre-check bypass, not only the heredoc false positive seen during PILOT-58.
- **The GitHub approval route doesn't compare the approver with the change's creator.** `lifecycle._approve_github` excludes only the PR author. `evidence_policy.check_write`'s `tier3-same-person` rule covers only the `prompt` and `tty` methods. `state.created_by` is a git email, and GitHub gives a login, so the two are never compared.
- **The final code review of `verify-range`** (CHANGELOG 2.1.0) left eight Mediums and Lows:
  1. a shared log merged with the base's lines first fails rule 4;
  2. `.evidence/context/` and `.evidence/decisions/` are ungated locally but must be claimed in CI;
  3. non-record files under `.evidence/changes/` and `.evidence/audit/` are exempt from claims;
  4. one session's log appended on both sides of a merge fails;
  5. whole-range log containment is by set, not by order;
  6. `CODEOWNERS` directory patterns without a slash are matched only at the top level;
  7. after a post-hook timeout, the alarm is not re-armed;
  8. `--o` for `--only` is not caught.
- **Hook before the permission prompt** (PILOT-58 intent, open question). The hook performs `evidence change start|advance` in PreToolUse, before Claude Code's prompt.

## Proposed outcome
1. Concurrent tool calls are each charged only with what they could have done:
   - no call erases another call's record, or a human's signed record, written during its window;
   - no call is blamed for another call's declared writes;
   - replaying an older signed record is still undone.
2. Every allowed tool call leaves a pre-call audit entry, and a call whose post never runs is still checked.
3. The monitor cannot be stalled by special files, checks the tree the command ran in, and keeps its snapshots private.
4. The Bash pre-check sees every command on every line.
5. A GitHub approval by the change's creator does not satisfy Tier 3.
6. The eight `verify-range` review items are fixed or explicitly decided.

**Measure:**
- zero false `control-plane` or duplicate violations across a session with three parallel review subagents and main-session edits (MAN-CON-01);
- a human `clear-violations` mid-call stays cleared (MAN-CON-02);
- every new tolerance has a negative test: a replayed signed record, a write that no overlapping call declared, an unsigned attestation, and a deleted or forged lease.

## Affected users and systems
- The gate engine: integrity monitor, hooks, audit log, Bash parser, approval route and `verify-range`.
- Every repository that runs the plugins, and teams that fan out subagents.

## Regulated record impact
Yes. The change adds an attestation log under `.evidence/audit/`, adds group-attribution fields to violation records, and changes when the monitor restores signed records. Every record stays signed and append-only.

## Compliance evidence impact
Yes. `SECURITY.md`, `governance/control-mapping.md` and `governance/supplier-audit-packet.md` describe the monitor's restore behaviour and its known concurrency gap. These are restated. No regulatory framework is established for this repository (`.evidence/context/compliance.md`: all `[ASK]`).

## Data classification
None. The signing key is a secret that must never be read or exposed. Snapshots hold copies of configuration files, and this change makes them private.

## Constraints
- **No weakening of what merges.** `verify-range` (ADR-0004) stays authoritative. The rule 4 and rule 2 changes accept only what the review showed to be legitimate, and each has a negative test.
- **No laundering:** running calls in parallel must never make a write acceptable that the pre-check would have denied in any overlapping call.
- **Fail closed:** a missing, altered or unreadable lease, snapshot or attestation is a violation, never a skipped check.
- **Backwards compatible:** 2.1–2.3 snapshots, records and audit logs still verify, and a snapshot taken by the previous engine version is paired once without a violation.
- **Tier 3 process:**
  - plan approval by a second human (Harshil);
  - review agents run one at a time;
  - no edits during a review;
  - merges after PILOT-62 and PILOT-60.

## Out of scope
- Key isolation (PILOT-61).
- Release automation (PILOT-63).
- Re-approval history and `CLAUDE_CONFIG_DIR` watching (PILOT-64 proposal).
- A human's own editor writes mid-call to files outside the control plane. They are still judged as the call's, as today.
- Approve, clear, release and merge stay human-only.

## Open questions
- **Split into 59a (concurrency) and 59b (deferrals)?** Recommended in the plan. Owner: maintainer.
- **Does Claude Code send PostToolUse for an interrupted Bash call, or for `run_in_background: true` only at launch?** Is there a failure event? Owner: plan step 1 [NEEDS VERIFICATION].
- **The contents of review nits 2–5.** Owner: maintainer.
- **Hook before the prompt:** accept, as the spec proposes, or act only in non-prompting modes? Owner: maintainer.
- **GitHub identity of the creator:** capture `gh api user` at `change start`, or an org map `approval.github_identities` (email → login), or both? Owner: maintainer.
