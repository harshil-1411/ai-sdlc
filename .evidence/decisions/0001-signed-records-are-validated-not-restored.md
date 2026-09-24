# 0001. Validate engine-written records by signature; serialise Bash monitoring

Status: Proposed
Date: 2026-09-24
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-58   Spec: intent/2026-09-24-integrity-monitor-hardening/spec.md
Supersedes: none
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- The integrity monitor (`integrity.py`) snapshots every control-plane file before each
  allowed Bash call. After the call, it restores anything that changed and removes anything
  created.
- Some control-plane files are written by the engine itself, from any concurrent hook:
  - audit logs;
  - `violations.json` and `.evidence/violations/*`;
  - `state.json`;
  - `approval.json`.
- On 2026-09-24, parallel review subagents and a second session in the same folder produced
  these failures:
  - false violations;
  - a `violations.json` restored over a newer, real record, erasing a violation;
  - a read-only reviewer blamed for the main session's edits.
- The monitor diffs the whole working tree, so any write inside another call's window is
  attributed to that call.
- Since 2.0.1, every engine write is HMAC-signed and done through `state.write_file` /
  `open_append`, and every reader verifies the signature.

## Decision
1. **Signed records are judged by signature, not by change.** For engine-written, signed
   control-plane records, the monitor verifies the current file after a call:
   - valid signature (and hash chain, for audit logs): legitimate, whoever wrote it;
   - invalid or missing signature: a violation, and the file is quarantined, not deleted.

   The monitor never restores or removes these files. Unsigned control-plane files keep
   today's snapshot-restore behaviour:
   - `.claude/**`;
   - `.evidence/policy.json`;
   - `.evidence/secrets-allowlist.json`;
   - `managed-settings.json`;
   - `.mcp.json`.
2. **Bash monitoring is serialised per repository.** PreToolUse takes a repository monitor
   lease before snapshotting, and PostToolUse releases it after checking. A second
   allowed Bash call waits for the lease, up to a bound (15 s by default; the PreToolUse hook
   timeout is 30 s). The lease is an O_EXCL file under
   `.git/` holding the session, tool_use_id and expiry, with a time-to-live so a killed
   call cannot hold it forever. If the lease cannot be taken within the bound, the call is
   denied (fail closed), with a message saying so.
3. **A call that finds an expired lease from another call** records a
   `concurrent-unmonitored` note. It never produces a violation attributed to the new call.

## Consequences
- Easier: parallel subagents and a human's terminal no longer create false violations
  or erase real ones through restores. Signature checks were already the source of truth
  for these records, so the monitor now agrees with the readers.
- Harder:
  - parallel Bash calls in one repository now run one after another inside the monitor
    window, which adds latency when subagents fan out;
  - a long-running command holds the lease for its duration.
- Constrained: a signed-record type that isn't HMAC-signed cannot use rule 1. Every new
  engine record must be signed.
- Cost to reverse: moderate. The lease is additive, and rule 1 can be switched back by
  policy.
- Review trigger: reopen if Claude Code exposes a per-call working-tree view or
  per-call file attribution, or if lease waits exceed the hook timeout in practice.

## Alternatives
| Option | Why it lost |
| --- | --- |
| Keep snapshot-restore for every control-plane file | Restores over legitimate concurrent engine writes (the observed data loss) |
| Attribute changes to all overlapping calls | Still false positives, and it lets an agent launder writes by running calls in parallel |
| Per-call filesystem views (overlay, copy-on-write) | Not available to hooks; far larger change |
| Deny parallel tool calls outright | Breaks legitimate subagent fan-out; serialising only the monitor window is enough |
