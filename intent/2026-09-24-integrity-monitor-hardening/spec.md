# Spec: Integrity-monitor and engine hardening
Tracker: PILOT-58   From: intent/2026-09-24-integrity-monitor-hardening/intent.md
Risk tier: 3 — changes the integrity monitor, audit log, commit gate and git execution inside unsandboxed hooks that hold the signing key; the policy floor `**/audit/**` applies to audit handling, and the change alters the framework's own tamper-evidence claims.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Requirements
| ID | Requirement | Source (intent.md section) | Acceptance |
| --- | --- | --- | --- |
| REQ-IMH-01 | The monitor never removes or restores a file through a symlinked path component, and never touches a path outside the repository | Problem: F1 | Engine test: `.evidence/violations/x -> <outside dir>` created by an unparsed program → the outside files are untouched, a violation is recorded |
| REQ-IMH-02 | A non-regular entry (directory, FIFO, symlink) at a violations-record path is itself an open violation, so the push gate stays closed | Problem: F4 | Engine test: a directory at `.evidence/changes/K/violations.json` → push denied with a violations message |
| REQ-IMH-03 | Engine-written signed records are validated by signature, never restored or removed by the monitor; an invalid one is quarantined and recorded (ADR-0001) | Problem: concurrency | Engine tests: a concurrent valid engine write during another call's window → no violation, not restored; a forged unsigned `approval.json` → quarantined + violation |
| REQ-IMH-04 | Allowed Bash calls in one repository are monitored one at a time through a lease with a time-to-live; a call that cannot take the lease within the bound is denied; an expired lease is noted, never blamed on the new call (ADR-0001) | Problem: concurrency | Engine tests: two overlapping calls from different sessions → the second waits, and a write by the first is attributed only to the first; an expired lease → note, no violation; lease held past the bound → deny |
| REQ-IMH-05 | The directories `.evidence`, `.evidence/audit`, `.evidence/changes`, `.evidence/violations` are control plane: a change to their type, mode or ownership is a violation | Problem: directory globs | Engine test: `chmod 555 .evidence/audit` by an unparsed program → violation |
| REQ-IMH-06 | If a call's own PostToolUse audit entry cannot be written, a violation is recorded (branch-level) and the next call is denied | Problem: own-log unwritable | Engine test: an unparsed program makes the log read-only → violation recorded, next pre denies |
| REQ-IMH-07 | Deleting a file inside an untracked directory during a call is judged like any other delete | Problem: untracked deletes | Engine test: an unclaimed untracked file deleted by an unparsed program → violation |
| REQ-IMH-08 | Integrity snapshots are written only into a per-user, non-symlinked directory with mode 0700, through O_EXCL/O_NOFOLLOW | Problem: temp snapshots | Engine test: a planted symlink at the snapshot directory → the snapshot is refused, and the call is denied (fail closed) |
| REQ-IMH-09 | Every git process the engine starts runs with command-executing configuration neutralised, and the hook refuses to run git in a repository whose local config defines a command-executing key not allowed by policy | Problem: hook git | Engine test: `.git/config` with `core.fsmonitor = <marker script>` → the marker never runs; the call is denied with a message naming the key |
| REQ-IMH-10 | A commit's evidence, claims and secret checks cover exactly what the commit records: pathspec/`--only`/`--include` commits are denied; `-a` includes tracked working-tree changes in the checks | Problem: commit bypass | Engine tests: `git commit -m … -- src/unclaimed.py` → deny; `git commit -am` with an unstaged secret in a tracked file → deny |
| REQ-IMH-11 | `audit verify` rejects any entry whose hash already appeared earlier in the log (a replayed entry), in addition to today's fork rule | Problem: fork rule | Engine test: A,B,B',B → fail |
| REQ-IMH-12 | `run-tests.sh` runs `evidence gaps --strict` last, against the results it just wrote, to a configurable results directory; the content suite no longer runs the self-check; CI's signed gate stays the merge gate (ADR-0002) | Problem: committed results | Content test: run-tests.sh ends with the gaps step and honours `EVIDENCE_RESULTS_DIR`; a fresh local run passes in one pass with no file under `validation/` changed |
| REQ-IMH-13 | The adapter YAML reader strips inline `# comments` outside quotes | Problem: YAML comments | CLI test: `- plan/*.md  # note` parses to `plan/*.md` |
| REQ-IMH-14 | A requirement ID in `plan/*.md` defines a requirement only when no spec defines it, so a Tier 2+ plan under `plan/` causes no DUPLICATE-ID | Problem: DUPLICATE-ID | CLI test: a spec and a `plan/` Proof table sharing an ID → no DUPLICATE-ID, the spec is the definition |
| REQ-IMH-15 | A temp-directory argument is judged as script execution only when the program executes its argument (interpreters, shells, `make -f`, `source`); `curl -o`, `mkdir`, `tail`, `cat` on temp paths are allowed | Problem: false positives | Engine tests: `python3 /tmp/x.py` → deny; `mkdir -p $TMPDIR/…`, `curl -o /tmp/x`, `tail /tmp/x.log` → allow |
| REQ-IMH-16 | `engine-tests.py -k <filter>` never crashes because a skipped case skipped setup | Problem: -k crash | Running `-k "REQ-SLF-07 20"` exits 0 when the case passes |
| REQ-IMH-17 | A plan re-approval appends a `re-approved` history entry to the change state, whatever the stage | Problem: history | Lifecycle test: approve, edit plan, approve again → two approval entries in history |
| REQ-IMH-18 | `governance/control-mapping.md`, `governance/supplier-audit-packet.md`, `HANDOFF.md` and the 2.0.x Known issues match the shipped behaviour | Compliance evidence impact | Content test: no Known-issues item marked fixed remains listed; the supplier packet describes signature validation of records |

## Design
Existing components reused: `state.write_file` / `open_append` / `_dir_fd` (the safe writers from 2.0.1), `signing.verify`, `integrity.snapshot/check`, `evidence_policy._check_commit`, `cmdparse`, `evidence_trace.load_adapter`.

- **REQ-IMH-01, 07, 05 (`integrity.py`):**
  - `_control_plane_files` walks with `os.walk(followlinks=False)` and `lstat`. A symlink found at a control-plane path is recorded as a violation, never followed.
  - Removal goes through a new `state.remove_file(root, rel)`, which unlinks through `_dir_fd` (O_NOFOLLOW components), so a symlinked parent raises. Paths whose realpath is outside the root are never removed.
  - Untracked entries record their status in the snapshot, so a deleted untracked file is judged as a delete.
  - The four `.evidence` directories are snapshotted by `lstat` (type, mode, uid) in `extras`.
- **REQ-IMH-02 (`state.py`):** `_read_violations` checks `lstat` first. Anything that is not a regular file returns an open violation entry, "violations record is not a file". `open_violations` therefore blocks.
- **REQ-IMH-03 (`integrity.check`):** control-plane paths split into *signed records* and *unsigned config*.
  - Signed records: `.evidence/changes/*/state.json`, `approval.json`, `violations.json`, `.evidence/violations/*`, `.evidence/audit/*.jsonl`.
  - Unsigned config: everything else.
  - For signed records: if the file verifies (and, for audit logs, chains with no new break), accept. Otherwise move it aside with `os.rename` through a dir fd to `<name>.quarantined-<rand>` and record a violation. There is no restore or remove.
  - Unsigned mode (no key): record, as today.
- **REQ-IMH-04 (`integrity.snapshot/check`, `hook.run_pre/run_post`):**
  - The lease file is `.git/evidence-monitor.lease`, created O_EXCL with `{session, tool_use_id, expires}`.
  - PreToolUse retries for up to `policy.monitor_lease_wait_s` (default 15 s), then denies. The PreToolUse hook timeout is 30 s (`plugins/evidence-sdlc/hooks/hooks.json:16`), which leaves room for the snapshot.
  - PostToolUse removes the lease only if it holds it.
  - A lease whose `expires` has passed is taken over, with a `concurrent-unmonitored` note.
  - The TTL is `policy.monitor_lease_ttl_s` (default 600 s).
  - The snapshot records the lease token, so a post that doesn't own the lease records "integrity-lease-lost" rather than judging.
- **REQ-IMH-06 (`hook.run_post`):** if `_audit` raises for the post entry, `record_violations(branch-level, "audit-unwritable")` runs. The next `run_pre` already denies through `audit_ready`.
- **REQ-IMH-08 (`integrity._snap_path`):** the directory is `<tempdir>/evidence-chain-snapshots-<uid>/<session>`.
  - Created 0700.
  - `lstat` must show a directory owned by the uid and not a symlink.
  - Files are written through `state.write_file`, anchored at that directory.
- **REQ-IMH-09 (`state.git` plus the 6 other direct `subprocess.run(["git", …])` sites):** one helper, `st.run_git(args, cwd)`.
  - Prepends `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c core.pager=cat -c diff.external= -c protocol.ext.allow=never`.
  - Sets `GIT_CONFIG_NOSYSTEM=1`.
  - Before first use per call, parses `.git/config` (and `include.path` files) for command-executing keys: `core.fsmonitor`, `core.hooksPath`, `core.sshCommand`, `core.editor`, `filter.*.{clean,smudge,process}`, `diff.*.{command,textconv}`, `merge.*.driver`, `credential.helper`.
  - Refuses if any is present and not in `policy.git_allowed_config` (default: `filter.lfs.*`).
- **REQ-IMH-10 (`evidence_policy._check_commit`):** a pathspec after `--`, or a trailing path argument, `--only`/`-o`, or `--include`/`-i` → deny ("stage what you commit, then `git commit` without paths"). For `-a`, the checked set is staged ∪ `git diff --name-only`, and the secret scan reads working-tree content.
- **REQ-IMH-11 (`state.audit_verify`):** keep a set of seen hashes; a repeat is a break.
- **REQ-IMH-12:**
  - `run-tests.sh`: `EVIDENCE_RESULTS_DIR` defaults to a directory outside the working tree (`$TMPDIR/evidence-results/<repo-hash>`), and `.github/workflows/ci.yml` sets `validation/results`.
  - The last step runs `evidence gaps --strict --results "$dir"` and writes `gaps.xml` (a REQ-V2C-09 case).
  - The adapter gains `self_check_requirement: REQ-V2C-09`, which `gaps` skips in UNVERIFIED-RESULT.
  - The content-suite REQ-V2C-09 block is replaced by a structural check on run-tests.sh (ADR-0002).
- **REQ-IMH-13 (`evidence_trace` YAML reader):** strip ` #…` outside quotes.
- **REQ-IMH-14 (`evidence_trace` requirement scan):** scan `intent/*/spec.md` first, then plan globs. For a plan, an ID already defined by a spec is a reference, not a definition.
- **REQ-IMH-15 (`evidence_policy`, the temp-argument loop at `:779-785`):** apply the temp-dir script check only when `s.prog` is in an `EXECUTES_ARG` set (python*, node, ruby, perl, bash, sh, zsh, make, go, swift, osascript, php, deno, bun, source, `.`). Otherwise skip.
- **REQ-IMH-16:** `suite_round4` creates `s1.jsonl` itself rather than relying on a filtered case.
- **REQ-IMH-17 (`lifecycle.write_approval`):** always append a history entry: `approved` when advancing, `re-approved` otherwise.
- **REQ-IMH-18:** docs and governance text, with the content check.

## Regulatory control impact
`.evidence/context/compliance.md` establishes no applicable framework for this repository (all `[ASK]`), so no control set is loaded.

| Framework | Control ID | Applies? | How it is satisfied | Evidence |
| --- | --- | --- | --- | --- |
| none established | — | N/A | compliance.md lists none; awaiting maintainer | `.evidence/context/compliance.md:36` |

The framework's own claims for adopters change: `governance/control-mapping.md` maps SOC 2 CC8.1, ISO 27001 A.8.32 and NIST SSDF PW.4 to audit-log and violation tamper-evidence. REQ-IMH-18 re-checks those rows.

## Evidence impact
- New rows: REQ-IMH-01..18.
- Modified proof: REQ-V2C-09 moves from a content-suite check to the final `run-tests.sh` step (ADR-0002); its old test is retired in the same change.
- REQ-V2G-09 (control-plane protection) and REQ-V2A-02 (audit) gain the new behaviour. Their existing tests must still pass, or be listed with the reason they changed (restore to quarantine).
- `validation/results/` becomes historical (ADR-0002).
- Re-verification: every repository running 2.0.x should redeploy, because this closes High findings (F1, F4). The CHANGELOG says so.

## Diagrams
- Sequence, monitor lease (REQ-IMH-04):

```mermaid
sequenceDiagram
  participant A as Call A (pre/post hooks)
  participant B as Call B (pre/post hooks)
  participant L as .git/evidence-monitor.lease
  A->>L: O_EXCL create {A, expires}
  A->>A: snapshot; command runs
  B->>L: O_EXCL create → exists; wait ≤ 20 s
  A->>A: check (signed records validated, not restored)
  A->>L: remove (owner = A)
  B->>L: O_EXCL create {B, expires}
  B->>B: snapshot; command runs; check; release
  Note over A,B: trust boundary — hooks run unsandboxed with the key
```

## Security design
- **Trust boundary:** hooks, unsandboxed and holding the key, act on paths and repository config that the sandboxed agent can shape. Every new filesystem action goes through dir-fd, O_NOFOLLOW helpers (REQ-IMH-01, 08). Every git process has command-executing config neutralised, or refused (REQ-IMH-09).
- **Lease abuse:** an agent could hold the lease with a long-running command to stall other calls. That is bounded by the TTL, and it's the agent's own session. A lease file forged by the agent's shell under `.git/` is harmless: a forged `expires` far in the future stalls calls until the wait bound, then denies (fail closed). A forged expired lease is only taken over.
- **Quarantine versus deletion:** a record that fails verification is never deleted. It is moved aside and recorded, so an agent cannot destroy evidence by corrupting it.
- **Fail-closed preserved:** each new tolerance has a test proving the attack it guards against is still stopped (REQ-IMH-03 forged approval, REQ-IMH-11 replay, REQ-IMH-15 interpreter on temp file).
- Required review agents (Tier 3, per `evidence change status PILOT-58`): verifier, security-reviewer, code-reviewer. Run one at a time, with no edits while they run.

## UX
| State / concern | Behaviour |
| --- | --- |
| Error | Every new denial names the next action: waiting for the lease, stage then commit without paths, the refused git config key and the policy setting that allows it |
| Success | No new output on the normal path; parallel calls are slower by at most the lease wait |
| Edge cases (long values, zero, maximum, unusual input) | A killed call leaves a lease that expires after the TTL; take-over is noted |

Component reuse: N/A — no UI.

## Areas of concern
- **Hook acting before the permission prompt** (intent open question 1). Proposal: accept for now, since the managed settings allow `evidence change …` without a prompt anyway. Document it in `docs/managed-settings.md`, and revisit if a deployment needs the prompt. Owner: maintainer — decide at plan approval.
- **Content self-check design** (intent open question 2). Resolved by the proposal in ADR-0002. Owner: maintainer — accept or reject the ADR at plan approval.
- **Second CODEOWNERS reviewer** (intent open question 3). This isn't a code decision. Until one exists, Tier 3 merges need the admin override. Owner: maintainer.
- **Lease wait against the hook timeout.** Checked: the PreToolUse hook timeout is 30 s, and the default wait is 15 s. A command that runs longer than 15 s makes a parallel call wait and then be denied. That's acceptable fail-closed behaviour; the denial says to retry.
- **Git-LFS and other legitimate filters.** Defaulting `git_allowed_config` to `filter.lfs.*` may be too narrow for some orgs. The refusal message names the policy key to extend.

## Architecture decisions
| ADR | Created / Supersedes / Relies on | Status |
| --- | --- | --- |
| `.evidence/decisions/0001-signed-records-are-validated-not-restored.md` | Created | Proposed |
| `.evidence/decisions/0002-ci-owns-test-results.md` | Created | Proposed |
| HANDOFF.md "Decisions worth knowing": signing key held by hooks | Relies on | informal (no ADR yet) |

## Rejected alternatives
- **Split PILOT-58 into several smaller changes.** Rejected because the concurrency and signed-record decisions (ADR-0001) change how F1, F4 and the directory checks are implemented. Doing them separately would rework the same monitor code three times. Review trigger: if the plan exceeds about 1500 changed lines, split out REQ-IMH-12..17 (harness and usability) as a Tier 1/2 change.
- **Also see the Alternatives tables in ADR-0001 and ADR-0002.**
