# 0006. The integrity monitor tracks call windows with signed leases, judges engine records by attestation, and chains its snapshots

Status: Proposed
Date: 2026-09-25
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-59   Spec: intent/2026-09-25-concurrency-and-deferrals/spec.md
Supersedes: none (replaces the rejected ADR-0001)   Relies on: ADR-0003 rev. 2, ADR-0004 rev. 3, ADR-0005
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- The monitor snapshots the control plane and the dirty tree before each allowed Bash call, and compares after it (`integrity.snapshot` / `check`). Anything written inside the window is charged to that call.
- With overlapping calls, this was reproduced on `7759c17` (see the PILOT-59 intent):
  - another call's write is charged twice;
  - another session's freshly written `violations.json` is removed (signed mode), erasing its entry;
  - a human's signed `clear-violations` during a call is reverted.
- ADR-0001 was rejected, for three reasons:
  - accepting any validly signed record lets an older one be replayed;
  - its lease was unsigned;
  - losing the lease, or its expiry, skipped judgement.

## Decision
1. **Windows and signed leases.** Every allowed Bash and edit-tool call opens a window: a signed lease in `<git common dir>/evidence-monitor/` (0700, owner-checked). The lease carries the call's identity, a signed monotonic `seq`, the snapshot's hash and the writes the pre-check declared and allowed. The post pairs with its own lease by `(session, tool_use_id)` and then closes it.
   - The lease **protects** attribution, pairing and liveness.
   - It does **not** serialise commands. Only the monitor's seconds-long critical sections are serialised, under an `flock`.
2. **Failure modes fail closed:**
   - a missing or altered own lease is a violation;
   - an invalid foreign lease counts as an unknown overlapping window;
   - a lock timeout denies the pre and is recorded at the post;
   - an expired lease (no post) is checked later against the current tree, never skipped.
3. **Attested engine writes.** Every write of an engine-owned record (state, approval, violations) is first recorded in the signed, chained `.evidence/audit/attestations.jsonl`, and the file is written only after that.
   - A record changed during a window is kept only if its bytes match an attestation made inside that window.
   - Otherwise it is restored to the chained target: the latest attested content in the window, else the pre snapshot.
   - A replayed older signed record therefore does not pass.
   - Human CLI and prompt-channel writes are attested too, so mid-call human actions stand.
4. **Overlap attribution without laundering.** A changed path is explained only by an overlapping window's declared, pre-allowed writes. Any other change is judged under every overlapping window's context, is a violation if any judge denies it, and is recorded once with the group.
5. **Chained snapshots.** Each snapshot names the previous post's signed digest and `seq`. A change between calls is logged, not charged. A broken chain is a violation. A background window stays open until its TTL.
6. **Hook before the prompt** (the PILOT-58 open question) is accepted. The hook performs only agent lifecycle stages, which are signed and audited.

## Consequences
- **Easier:**
  - parallel subagents and a second session no longer create false violations or erase records;
  - a human can clear or approve while the agent works;
  - interrupted calls are checked.
- **Harder:**
  - monitor critical sections are serialised per repository, so a large tree adds latency to parallel calls, bounded by `monitor_lock_wait_seconds`;
  - every engine record write appends an attestation.
- **Constrained:**
  - a new engine-owned record type must be written through `st.attested_write`;
  - one session's log merged on both sides stays unsupported.
- **Cost to reverse:** moderate. The attestation log is additive, and the lease protocol can be bypassed by policy only in unsigned mode, where nothing is restored anyway.
- **Review trigger:** reopen if Claude Code exposes per-call file attribution or working-tree views, or if `monitor-busy` denials are seen in practice.

## Alternatives
| Option | Why it lost |
| --- | --- |
| ADR-0001 (accept any signed record; unsigned lease) | Replay and rollback; a fail-open lease |
| Serialise whole Bash calls | A long command blocks every other call; subagent fan-out stops |
| Charge every overlapping call | False positives and the observed data loss |
| Accept a change any overlapping call could have made | Laundering through parallel calls |
| Per-call filesystem views (overlay, copy-on-write) | Not available to hooks |
| Lease in `$TMPDIR` | Shared on Linux, and possibly different between hooks and the human terminal |
