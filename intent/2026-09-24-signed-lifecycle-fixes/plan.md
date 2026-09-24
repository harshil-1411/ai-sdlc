# Plan: Make the v2 lifecycle work end to end in a signed deployment
Tracker: PILOT-57   From: intent/2026-09-24-signed-lifecycle-fixes/spec.md   Date: 2026-09-24
Risk tier: 2 — gate-engine lifecycle, commit gate and integrity monitor fixes; no policy tier floor applies to `plugins/evidence-sdlc/scripts/engine/**`. Tier set by the human.

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Files claimed
- `intent/2026-09-24-signed-lifecycle-fixes/**`
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`
- `plugins/evidence-sdlc/scripts/engine/hook.py`
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
- `plugins/evidence-sdlc/scripts/engine/integrity.py`
- `plugins/evidence-sdlc/scripts/engine/state.py`
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`
- `tests/content_acceptance_tests.py`
- `docs/managed-settings.md`
- `plugins/*/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `CHANGELOG.md`
- `validation/results/**`

Overlap: PILOT-54 (not approved; its state.json is unsigned and must be restarted anyway, spec "Evidence impact") also claims `plugin.json`, `marketplace.json` and `CHANGELOG.md`. Sequence: **PILOT-57 merges first** and takes version 2.0.1. PILOT-54 is restarted afterwards, and its plan is revised to 2.0.2 and re-approved.

## Files that change
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`:
  - `_human_tty` (`:27-33`) returns a two-handle text wrapper (REQ-SLF-01).
  - New `_require_key_if_signed(root)`, called before `_human_tty()` at `:263`, `:289` and `:358` (REQ-SLF-05).
- `plugins/evidence-sdlc/scripts/engine/hook.py`: in `run_pre` (`:78`), before judging a Bash call, detect a lifecycle-only command (`change start|advance`, with `cd` glue only). Run `lifecycle.main(argv)` in-process with captured output and cwd, and return a deny whose reason carries `Done by the gate engine:` and the output. Deny "run it as its own command" when it is chained with any other program (REQ-SLF-04).
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`: in the commit check (`:393-407`), apply the prefix rule for the session audit log (REQ-SLF-02). Reuse `_is_evidence_cli` (`:545`) from `hook.py`.
- `plugins/evidence-sdlc/scripts/engine/integrity.py`:
  - `_dirty` (`:88-94`) emits per-file entries for collapsed untracked directories (REQ-SLF-03).
  - `cli_writes` (`:118-123`) drops the `change start/advance` branch, which the hook now performs. It keeps `approve --github-pr` and `--quick` is handled by the hook path.
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`: new cases for REQ-SLF-02, 03 and 04 (with and without key, using the existing `"k" * 40` key pattern at `:667-739`).
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`: new cases for REQ-SLF-01 (`os.openpty` slave passed to `_human_tty`) and REQ-SLF-05.
- `tests/content_acceptance_tests.py`: REQ-SLF-06 doc check.
- **Revision 2 (after the final security review and the audit-fork finding; voids approval af66ced428c6):**
  - `plugins/evidence-sdlc/scripts/engine/state.py`:
    - `audit_append` (`:457-472`) takes `fcntl.flock(LOCK_EX)` on the log and reads the last hash under the lock (REQ-SLF-07).
    - `audit_verify` (`:475-496`) takes an optional `warnings` list and accepts a sibling fork as a warning (REQ-SLF-08).
  - `lifecycle.py` `cmd_audit` prints those warnings.
  - `evidence_policy.lifecycle_call`: refuses any option other than `--tier`/`--kind` (with their values) and the positional stage (REQ-SLF-09a). The session repository comes from `CLAUDE_PROJECT_DIR` when set (09b).
  - `hook.lifecycle_decision`: refuses when `ctx.agent_type` is in `read_only_agents` (09c). It sets `EVIDENCE_LIFECYCLE_VIA=hook:<session>` for the in-process call, and `lifecycle` records it in the history entry (09d).
  - `lifecycle._artifact_path`: case-insensitive comparison, and `..` means a leading `..` component only.
  - `docs/managed-settings.md` and the key message: the one-command form `EVIDENCE_SIGNING_KEY="$(…)" evidence …`.
  - `CHANGELOG.md`: the items above.
  - Tests: as listed in spec rows REQ-SLF-07..09.
- `docs/managed-settings.md` "Signing key" section: human terminal actions need the key (one-shot `export … ; unset` recipe, without printing it). An agent's `change start/advance` is done by the hook. Note the audit-log prefix rule.
- Versions: all five `plugin.json` and `marketplace.json` go 2.0.0 → 2.0.1. `CHANGELOG.md` gets a `## 2.0.1 — 2026-09-24 (PILOT-57)` entry.

## Order of work
1. Write the failing tests first, for REQ-SLF-01..05. Run them and record that each fails for the reason in the spec's defect table. `evidence change advance PILOT-57 failing-test` is run after approval (kind fix).
2. REQ-SLF-01 TTY wrapper. (Independent.)
3. REQ-SLF-03 per-file untracked entries. (Independent.)
4. REQ-SLF-02 audit prefix rule. (Independent.)
5. **CHECKPOINT:** re-read spec.md, and confirm steps 2–4 changed only what the spec's Design says. Run the full engine suite: every pre-existing case must still pass unchanged.
6. REQ-SLF-04 hook-performed lifecycle calls, plus the `cli_writes` trim. This is the riskiest step.
7. REQ-SLF-05 key-required check for human actions.
8. Docs (REQ-SLF-06), version bump, CHANGELOG.
9. Run `bash scripts/ci/run-tests.sh`, `bash scripts/ci/check-version-bump.sh origin/main` and `evidence gaps --strict`. Dispatch the `verifier` and `security-reviewer` agents.
10. Commit. The agent cannot commit until step 4 is live, because hooks read script content live and `evidence_policy.py` is a script. If the agent's commit is still denied, the human commits from their own terminal. Push the branch and open a PR. A human merges.

## Mid-flight checkpoint (Tier 2/3)
Step 5.

## Reuse decisions
- Command parsing reuses `cmdparse.split_simple` and `evidence_policy._is_evidence_cli`. Signing reuses `signing.sign/verify` via `state.save_state`. The lifecycle operation reuses `lifecycle.main` unchanged, so there is no parallel implementation of start/advance in the hook.
- Tests extend the two existing engine/lifecycle suites and their helpers. No new suite is added.

## Risks
- **Step 6 is the riskiest.** Performing an operation inside PreToolUse is new for this engine. A bug there fails closed (the hook denies), and the human can still start changes from a terminal with the key. Rollback: revert the `hook.py` hunk; the CLI then runs in the sandbox as before.
- Step 4 could weaken the evidence rule too far. Mitigation: prefix only, audit log only, with tests for the altered and never-staged cases.
- Step 3 could make snapshots slower on repos with large untracked directories. It uses the same walk and cap as today; only the output shape changes.
- Existing tests that assert `cli_writes` behaviour for `change start` may need updating. Any such edit is listed in the PR, with the reason.

## Proof

| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| REQ-SLF-01 | unit (pty) | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-SLF-01 …" | validation/results/lifecycle.xml |
| REQ-SLF-02 | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-SLF-02 …" (allow on appended; deny on altered, never-staged, stale state.json) | validation/results/engine.xml |
| REQ-SLF-03 | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-SLF-03 …" (reset → no violation; new file in untracked dir → judged) | validation/results/engine.xml |
| REQ-SLF-04 | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-SLF-04 …" (signed start/advance; chained → deny, no state; unsigned Tier 2 → deny; agent `./evidence` never run) | validation/results/engine.xml |
| REQ-SLF-05 | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-SLF-05 …" | validation/results/lifecycle.xml |
| REQ-SLF-06 | content | yes | — | `tests/content_acceptance_tests.py` "REQ-SLF-06 …" | validation/results/content.xml |
| REQ-SLF-07 | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-SLF-07 …" (concurrent appends → no fork) | validation/results/engine.xml |
| REQ-SLF-08 | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-SLF-08 …" (fork → warning; deleted/altered/bad-sig → fail) | validation/results/engine.xml |
| REQ-SLF-09 | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-SLF-09 …" (artifact options refused; `.Claude/` refused; foreign `CLAUDE_PROJECT_DIR` refused; read-only agent refused; `via: hook` recorded) | validation/results/engine.xml |
| REQ-SLF-01, 04 (live) | manual | no | MAN-SLF-01 | — | After merge, in a real signed session: the agent starts a Tier 2 change via the hook; the human runs `clear-violations` in a terminal with the key; the agent commits. Transcript noted in the PR. |

## Considered and rejected
See spec "Rejected alternatives". Also rejected: splitting this into several changes. D2, D5 and D6 each independently block the next change, so fixing them one at a time would take several rounds of the human committing from a terminal.
