# Intent: Integrity-monitor and engine hardening (the deferred 2.0.x known issues)

Tracker: PILOT-58   Author: Suparn Bector (maintainer), drafted by Claude from session 1e01f04e findings   Date: 2026-09-24   Status: draft

## Problem
Dogfooding v2 on this repository (PILOT-54, PILOT-57) and five independent security reviews found weaknesses. Each is already present in 2.0.0–2.0.2, and all were deferred by the maintainer's decision. They fall into four groups.

**The integrity monitor can be turned against the repository, or misled:**
- **F1:** when a command creates a control-plane file, the monitor removes it through a path that follows symlinked directories. An agent can therefore make the unsandboxed hook delete files outside the repository.
- **F4:** a directory or other non-file planted at a violations-record path stops violations being recorded, and the push gate then reads none.
- **Concurrency:**
  - The monitor compares the whole working tree before and after each Bash call. With parallel subagents, or two sessions in one folder, it blames one call for another's writes and restores control-plane files over newer, legitimate records.
  - Observed on 2026-09-24: false violations, a restored-over violation record, and false violations in msb_clm-style use when the human ran tests while a session was active.
- The control-plane globs cover files but not the directories themselves, so a `chmod` of `.evidence/audit/` is judged as an ordinary write.
- A single allowed call can make its own session log unwritable before its post-call entry is written.
- Deleting a file inside an untracked directory is not judged.
- Integrity snapshots in the shared temp directory are written without symlink checks.

**Hooks run git unsandboxed, with the signing key in their environment:**
- Repository-level git configuration that executes commands (`core.fsmonitor`, hooks paths) is not neutralised.
- Reviewers rated this possibly Critical, but did not confirm it.

**Commit checks can be bypassed:**
- `git commit -- <paths>` / `--only` / `--include` commit working-tree content while the evidence, claims and secret checks inspect only the index.
- `audit verify` checks a fork only against the immediate predecessor. This is reachable only where the lock is unavailable.

**Usability defects that make every change cost human round trips:**
- **Committed results:** the content suite's self-check (REQ-V2C-09) reads the committed `validation/results/content.xml` before the suite writes a fresh one. For every change, the human has to run `run-tests.sh` twice and commit result files, and CI results are not the source of truth.
- The adapter's YAML reader keeps inline `# comments` as part of a value. This silently broke a glob in PILOT-54.
- A Tier 2+ plan saved under `plan/` repeats its spec's REQ IDs, which would show as DUPLICATE-ID.
- **Temp-directory false positives:** the gate treats any temp-directory argument as "running a script" (for example `curl -o`, `mkdir`, `tail` on a temp file).
- `engine-tests.py -k` crashes in `suite_round4`.
- A plan re-approval is not recorded in `state.json`'s history once a change is implementing.

**Who is affected:**
- Every team running Evidence Chain in a signed deployment, including msb_clm, which moved to v2 on 2026-09-24.
- Reviewers and auditors who rely on the violation records and audit logs.
- The maintainer, who carries the manual round trips.

## Proposed outcome
- **F1, F4 and the fsmonitor/hooks exposure:** closed, each with an engine test that reproduces the attack and shows it refused or recorded.
- **Concurrency:** a write made by one tool call is never attributed to another, and the monitor never restores over, or deletes, a violation or audit record. The engine test runs two overlapping calls, and the reviewer-in-parallel scenario from 2026-09-24 produces no false violation.
- **Commit checks:** a commit's checks apply to exactly what the commit records.
- **Committed results:** a change's requirements can be proven from CI's own signed results, with no human-committed result files. `run-tests.sh` passes in one run.
- **Usability defects:** each has a regression test.
- **Measure:**
  - zero open items in the 2.0.2 "Known issues" list, except any the owner explicitly accepts;
  - zero manual `validation/results` commits for PILOT-58 itself.

## Affected users and systems
- The gate engine: integrity monitor, commit gate, hooks, audit log, CLI adapter.
- CI (`scripts/ci/run-tests.sh`, `.github/workflows/ci.yml`).
- Every repository using the plugins, including msb_clm.
- Maintainers, reviewers and auditors.

## Regulated record impact
Yes. This changes how audit logs and violation records, the framework's own audit trail, are written, protected and verified. Nothing for end customers.

## Compliance evidence impact
Yes. `governance/control-mapping.md` and `governance/supplier-audit-packet.md` claim tamper-evidence for audit and violation records. Those claims must be re-checked against the new behaviour, and the known-issue caveats removed or restated. No regulatory framework is established for this repository (`.evidence/context/compliance.md`: all `[ASK]`).

## Data classification
None. No personal, payment or health data. The signing key is a secret that must never be read or exposed. No change may read it.

## Constraints
- **Backwards compatible for deployed repositories:**
  - existing signed state, approvals, violations and audit logs from 2.0.x must still verify;
  - existing forks stay reported as notes.
- **Tier 3:**
  - default permission mode;
  - a second human approver (Harshil) for the plan;
  - review agents run one at a time;
  - no edits while a review runs.
- **No weakening of fail-closed behaviour.** Any new tolerance needs a test showing the attack it was meant to stop is still stopped.
- **Must run on macOS and Linux (CI).** Tests that need a pty or chmod semantics say where they cannot run.

## Out of scope
- **Stays human-only:** approve, clear, release and merge.
- **No external red team or pilot program.** Those are owner actions.
- **No changes to the skills content,** apart from wording that points at changed engine behaviour.

## Open questions
- **Hook acting before the permission prompt.** Outside plan mode, the hook performs `evidence change start|advance` before Claude Code's permission prompt. Accept, or act only in non-prompting modes? Owner: maintainer.
- **Content self-check design.** Should REQ-V2C-09 move out of the content suite into a final CI step, or should the content suite ingest its own fresh results? Owner: maintainer (a design choice for spec).
- **CODEOWNERS second reviewer.** Is there a second reviewer with write access, so Tier 3 merges stop needing the admin override? Owner: maintainer.
