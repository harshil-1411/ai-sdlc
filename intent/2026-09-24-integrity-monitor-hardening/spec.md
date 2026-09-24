# Spec: Integrity-monitor and engine git hardening (security set)
Tracker: PILOT-58   From: intent/2026-09-24-integrity-monitor-hardening/intent.md
Risk tier: 3 — integrity monitor, audit log, commit and push gates, and git execution inside unsandboxed hooks that hold the signing key; the policy floor `**/audit/**` applies.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Scope after the design review (2026-09-24)
The first draft (REQ-IMH-01..18 with ADR-0001) failed security design review.
- ADR-0001 is rejected: it allowed replay of signed records, and it had an unsigned, bypassable lease.
- By the maintainer's decision, the work is split:

| Change | Scope | Tier |
| --- | --- | --- |
| **PILOT-58 (this spec)** | Confirmed security holes with contained fixes: F1, F4, engine-git neutralisation (ADR-0003), commit and push validation, audit-log integrity, `.evidence` directory checks, snapshot-directory safety | 3 |
| PILOT-59 | Concurrency: attested engine writes, a signed lease with holder liveness, chained snapshots, background writes (former REQ-IMH-03/04); new ADR | 3 |
| PILOT-60 | Usability: CI-owned results (ADR-0002 revised), adapter YAML comments, spec-before-plan IDs, inverted temp-script rule, `-k` crash, re-approval history (former REQ-IMH-12..17) | 2 |

The snapshot-restore behaviour for control-plane files, including signed records, is **kept** in PILOT-58. It is what stops rollback and deletion today.

## Requirements
| ID | Requirement | Source (intent.md section) | Acceptance |
| --- | --- | --- | --- |
| REQ-IMH-01 | The monitor lists the control plane without following symlinks, restores through `state.write_file` and removes through a dir-fd `state.remove_file`. It never acts through a symlinked component, never outside the repository, and reports a symlink at a control-plane path as a violation | F1 | Engine tests: `.evidence/violations/x -> <outside dir>` and `.evidence/changes/K -> <outside>` created by an unparsed program → outside files untouched, violation recorded |
| REQ-IMH-02 | A non-regular entry (directory, FIFO, symlink) at a violations-record path is an open violation, so the push gate stays closed | F4 | Engine test: a directory at `.evidence/changes/K/violations.json` → push denied |
| REQ-IMH-05 | A change to the type, mode or owner of `.evidence`, `.evidence/audit`, `.evidence/changes` or `.evidence/violations` during a call is a violation | Directory globs | Engine test: `chmod 555 .evidence/audit` by an unparsed program → violation |
| REQ-IMH-06 | If a call's own PostToolUse audit entry cannot be written, an `audit-unwritable` violation is recorded (branch level), and the next call is denied | Own-log unwritable | Engine test |
| REQ-IMH-07 | Deleting a file inside an untracked directory during a call is judged like any other delete | Untracked deletes | Engine test |
| REQ-IMH-08 | Integrity snapshots are written only into `<tempdir>/evidence-chain-snapshots-<uid>/<session>`, a directory owned by the uid, mode 0700 and not a symlink, through the safe writer. A planted link fails closed | Temp snapshots | Engine test |
| REQ-IMH-09 | Every engine git process runs through `state.run_git` with command-executing configuration neutralised and `GIT_*` scrubbed (ADR-0003 §1). Before git calls other than `rev-parse`, local and worktree config is read with `git config --list --show-scope --includes` and refused on any denied key unless the exact key=value is allow-listed. Refusal in PostToolUse records `git-config-refused`, and the non-git checks still run | Hook git | Engine tests, each with a marker script that must never run: `core.fsmonitor`; `diff.<drv>.command` + `.gitattributes`; textconv; `filter.x.clean`; `filter.lfs.clean = sh -c …` (value not allow-listed); config via `include.path`, `includeIf`, `config.worktree` and a `.git` file (`gitdir:`); `GIT_CONFIG_PARAMETERS` / `GIT_EXTERNAL_DIFF` in the inherited environment |
| REQ-IMH-10 | PreToolUse denies commits with a pathspec, `--only`, `--include`, `-p`, `--patch`, `--interactive` or `--pathspec-from-file`, and a `git commit` combined in one command with any index-changing git command. `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY` and `GIT_ALTERNATE_OBJECT_DIRECTORIES` are environment spoofing | Commit bypass | Engine tests per form |
| REQ-IMH-19 | The push gate checks every commit in `merge-base(base, HEAD)..HEAD` against the committed trees: paths within the plan's claims (plus ungated and `.evidence/`), the change's evidence files present at the tip, and no secrets in added blobs (ADR-0003 §3) | Commit bypass | Engine tests: an unclaimed file committed via `commit-tree` + `update-ref`, via `GIT_INDEX_FILE`, and via a cherry-pick → push denied naming the commit and path; a secret added in an intermediate commit and removed later → push denied |
| REQ-IMH-11 | `audit verify` treats a repeated entry hash as a break, and requires every entry's `session` to match the log's own session (approval and clear logs excepted by name) | Fork rule | Engine tests: A,B,B',B → fail; another session's chain copied into the file → fail |
| REQ-IMH-20 | For each audit log, the integrity snapshot records `(size, sha256 of those bytes)`. After the call the old bytes must be an exact prefix of the log; a truncated, rewritten or replaced log is a violation. This replaces the size-only check | Audit-log integrity (review) | Engine test: same-length rewrite of an earlier entry → violation; replacement by another session's longer log → violation |
| REQ-IMH-21 | Push is denied for a keyed branch whose change directory or audit history exists but whose state is missing or fails verification | Review finding | Engine test: delete `state.json` (restored by the monitor) or quarantine it, then push → denied |
| REQ-IMH-22 | No engine module starts git except through `state.run_git` | ADR-0003 constraint | Engine test scans `plugins/evidence-sdlc/scripts/engine/*.py` for other `subprocess` git invocations |
| REQ-IMH-18 | `governance/control-mapping.md`, `governance/supplier-audit-packet.md`, `docs/policy-reference.md`, `docs/gates-reference.md`, `docs/managed-settings.md`, `HANDOFF.md` and the CHANGELOG Known issues match the shipped behaviour; items moved to PILOT-59/60 remain listed as known | Compliance evidence impact | Content test |

## Design
Components reused: `state.write_file` / `open_append` / `_dir_fd` (2.0.1), `signing`, `integrity.snapshot/check` (snapshot-restore kept), `evidence_policy._check_commit` and the push gate, the policy key `deny_git_config_keys`, `cmdparse`.

- **REQ-IMH-01 (`integrity.py`):**
  - `_control_plane_files` uses `os.walk(root, followlinks=False)` and matches paths against the globs with `lstat`. A symlink or non-regular file at a control-plane path is reported, never read through.
  - `check()` restores with `st.write_file(root, rel, old)` and removes with `st.remove_file(root, rel)`.
  - `remove_file` walks with `_dir_fd` (O_NOFOLLOW), then runs `os.unlink(name, dir_fd=…)`. It refuses if the final entry is a directory.
- **REQ-IMH-02 (`state._read_violations`):** `lstat` first; anything that isn't a regular file gives `[{"rule": "violations record is not a file", "open": True}]`.
- **REQ-IMH-05:** `_extras` records `lstat` `(S_IFMT, mode, uid)` for the four directories.
- **REQ-IMH-06:** `hook.run_post` runs `try: _audit_strict(...)`, and on failure `record_violations(branch-level, "audit-unwritable")`. The next PreToolUse is denied by `audit_ready`.
- **REQ-IMH-07:** snapshot `dirty` entries carry their porcelain status. After the call, a key present before and absent after, with status `??`, is judged as a delete.
- **REQ-IMH-08:** `_snap_path` creates the directory 0700 through `os.mkdir`, then checks `lstat`: a directory, owned by `os.getuid()`, not a link. Otherwise it raises, and PreToolUse fails closed. Files are written through `write_file` anchored at that directory.
- **REQ-IMH-09 (`state.run_git`, ADR-0003 §1–2):**
  - `env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}`, then `GIT_CONFIG_NOSYSTEM=1` and, when supported, `GIT_ATTR_SOURCE=<empty tree>`.
  - Args get `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c core.pager=cat -c diff.external= -c protocol.ext.allow=never`, plus `--no-ext-diff --no-textconv` for diff, log and show.
  - `check_git_config(root)` runs `run_git(["config", "--list", "--show-scope", "--includes"])` and checks keys at `local` or `worktree` scope against the deny set: the policy `deny_git_config_keys` ∪ `filter.*`, `diff.*.command`, `diff.*.textconv`, `merge.*.driver`, `core.askPass`, `core.gitProxy`, `core.sshCommand`, `core.worktree`, `gpg.*program`, `ssh.variant`, `remote.*.uploadpack`, `remote.*.receivepack`, `uploadpack.*`, `*tool.*.cmd`, `interactive.diffFilter`, `pager.*`, `url.*.insteadOf`.
  - An exact `key=value` in the org-policy `git_allowed_config` passes. The defaults are git-lfs's `filter.lfs.clean=git-lfs clean -- %f`, `filter.lfs.smudge=git-lfs smudge -- %f`, `filter.lfs.process=git-lfs filter-process` and `filter.lfs.required=true`.
  - The result is cached per hook process.
- **REQ-IMH-10 (`evidence_policy`):** the extra flag denials in `_check_commit`. The one-command rule: when a simple command is `git commit`, any other simple `git` whose subcommand is in {add, rm, mv, reset, restore, checkout, stash, apply, update-index, read-tree} → deny. The spoof list gets the three variables.
- **REQ-IMH-19 (push gate):** `range_problems(ctx, base)` runs `run_git(["rev-list", f"{base}..HEAD"])`, then for each commit `run_git(["diff-tree", "--no-commit-id", "-r", "--name-status", "--no-ext-diff", "--no-textconv", sha])`.
  - Claims are checked on added or modified paths.
  - Added blobs go to `secretscan` (size-capped).
  - Evidence files are checked at the tip.
  - The base comes from the push refspec target's remote-tracking ref, or `origin/<default>`. Without a base, it falls back to the pre-commit rules and says so.
- **REQ-IMH-11 (`state.audit_verify`):** a `seen` hash set, and a session check against `os.path.basename(path)` for `<session>.jsonl` logs.
- **REQ-IMH-20 (`integrity.snapshot/check`):** `audit` snapshot values go from `size` to `{size, sha256_prefix}`. After the call, the first `size` bytes are read and their hash compared.
- **REQ-IMH-21:** in the push gate (`_review_gate` path), if `key` and (`change_dir` exists or `audit_events` has a start for `key`) and `load_state` is None or fails verification → deny.
- **REQ-IMH-22:** a test greps the engine directory for `subprocess.run([\"git\"` and `"git",` outside `state.run_git`.

## Regulatory control impact
`.evidence/context/compliance.md` establishes no applicable framework for this repository (all `[ASK]`), so no control set is loaded.

| Framework | Control ID | Applies? | How it is satisfied | Evidence |
| --- | --- | --- | --- | --- |
| none established | — | N/A | compliance.md lists none; awaiting maintainer | `.evidence/context/compliance.md:36` |

For adopters, `governance/control-mapping.md` maps SOC 2 CC8.1, ISO 27001 A.8.32 and NIST SSDF PW.4 to change control and tamper-evidence. REQ-IMH-19 strengthens the change-control claim (commits validated as recorded), and REQ-IMH-20 strengthens the audit-log claim. REQ-IMH-18 updates those rows.

## Evidence impact
- New rows: REQ-IMH-01, 02, 05–11, 18–22.
- REQ-IMH-03, 04 and 12–17 are moved to PILOT-59/60 and are not defined here.
- Existing REQ-V2G-09 (control plane), REQ-V2A-02 (audit) and REQ-V2G-07/12 (commit) tests must still pass, or be listed in the PR with the reason.
- Re-verification: every 2.0.x deployment should upgrade (F1, F4 and the git exposure are High). The CHANGELOG says so.

## Diagrams
- Sequence, engine git call (REQ-IMH-09):

```mermaid
sequenceDiagram
  participant H as Hook (unsandboxed, has key)
  participant G as git
  H->>G: run_git(config --list --show-scope --includes) with -c neutralisations, GIT_* scrubbed
  G-->>H: key=value by scope
  alt denied key at local/worktree scope, value not allow-listed
    H-->>H: refuse (pre: deny; post: git-config-refused violation, non-git checks continue)
  else clean
    H->>G: run_git(status / diff --no-ext-diff --no-textconv / diff-tree …)
  end
  Note over H,G: trust boundary — repository config and attributes are agent-controlled
```

## Security design
- **Trust boundary:** repository-controlled git execution against the hook's key. ADR-0003 closes it at one entry point, enforced by REQ-IMH-22.
- **Commit integrity:** PreToolUse checks remain as early feedback. The push-time range check (REQ-IMH-19) is authoritative and does not depend on how the commits were made.
- **Audit integrity:** prefix-hash (REQ-IMH-20), replay and session binding (REQ-IMH-11), and the own-log failure record (REQ-IMH-06).
- **Kept behaviour:** snapshot-restore of control-plane files, which guards against rollback and deletion of signed records. The concurrency false positives it causes remain known issues until PILOT-59, which is stated in the CHANGELOG.
- Required review agents (per `evidence change status PILOT-58`): verifier, security-reviewer, code-reviewer, run one at a time.

## UX
| State / concern | Behaviour |
| --- | --- |
| Error | A git-config refusal names the key, its scope and the org-policy setting `git_allowed_config`. The push-range denial names the commit, the path and the rule |
| Success | No new output on the normal path |
| Edge cases (long values, zero, maximum, unusual input) | No base ref → push falls back to the pre-commit rules and says so. Very long branches → the range check is bounded by the commit count, and blob scans are size-capped |

Component reuse: N/A — no UI.

## Areas of concern
- **Repositories with local custom filters, diff drivers or credential helpers will be refused.** The deny set includes `credential.*`, which is common locally, and `includeIf` / `include.path`, which parse as includes but are not denied themselves. Default: deny local-scope credential helpers. They're rarely needed by the engine's read-only git calls, and the message explains the allow path. Owner: maintainer — accept at plan approval.
- **`GIT_ATTR_SOURCE`** needs git ≥ 2.40. On older git, the `--no-ext-diff --no-textconv` flags and the filter-key refusal remain the defence. Checked: git 2.46.0 locally. `run_git` detects support at runtime, so CI's git version doesn't change correctness.
- **Hook acting before the permission prompt.** Moved to PILOT-59, since it relates to the lease and its ordering. Owner: maintainer.
- **Second CODEOWNERS reviewer.** A separate owner action.

## Architecture decisions
| ADR | Created / Supersedes / Relies on | Status |
| --- | --- | --- |
| `.evidence/decisions/0003-hook-git-is-neutralised-and-commits-are-validated-at-push.md` | Created | Proposed |
| `.evidence/decisions/0001-signed-records-are-validated-not-restored.md` | Rejected in design review; its problem moves to PILOT-59 | Rejected |
| `.evidence/decisions/0002-ci-owns-test-results.md` | Deferred to PILOT-60, needs revision | Proposed |

## Rejected alternatives
- **One change for everything.** It failed design review as too large, with flawed concurrency and results designs. It is split by the maintainer's decision.
- **ADR-0001 (validate signed records by signature, lease).** Replay and lease bypasses; see its status line.
- **See also ADR-0003's Alternatives table.**
