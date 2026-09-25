# Plan: Local layer advisory — restored violations, user-config edits, Tier 3 auto modes behind the server gate
Tracker: PILOT-62   From: intent/2026-09-25-local-layer-advisory/spec.md   Date: 2026-09-25
Risk tier: 3 — integrity monitor, violation records, the Tier 3 permission-mode gate and `verify-range` rule 5. A second human approves (Harshil).

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Files claimed
- `intent/2026-09-25-local-layer-advisory/**`
- `.evidence/decisions/**`
- `plugins/evidence-sdlc/scripts/engine/integrity.py`
- `plugins/evidence-sdlc/scripts/engine/hook.py`
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
- `plugins/evidence-sdlc/scripts/engine/state.py`
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`
- `plugins/evidence-sdlc/policy/default-policy.json`
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`
- `plugins/evidence-sdlc/scripts/tests/fixtures/pilot62/**` (new: captured GitHub API responses)
- `tests/content_acceptance_tests.py`
- `docs/gates-reference.md`
- `docs/policy-reference.md`
- `docs/managed-settings.md`
- `governance/control-mapping.md`
- `governance/supplier-audit-packet.md`
- `SECURITY.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `plugins/*/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

Not changed: `.github/workflows/**`, `validation/**`, `scripts/ci/**`, `.claude/settings.json`.

## Files that change
- `plugins/evidence-sdlc/scripts/engine/integrity.py`:
  - `AUTO_RESOLVABLE` (rule and action pairs); the verified undo in `check` step 1 and 1a, which marks `resolved` (REQ-LLA-01, 02);
  - `_permission_grant` → `_local_settings_change` (REQ-LLA-05);
  - `_not_user_writable`, `_claude_json_projection`, and the per-kind `_extras` values and step-1b comparison (REQ-LLA-06, 07).
- `plugins/evidence-sdlc/scripts/engine/hook.py`, `run_integrity`:
  - the cap split (REQ-LLA-03);
  - `config-change` and `user-config-changed` audit events (REQ-LLA-05, 06);
  - per-class post messages (REQ-LLA-01).
- `plugins/evidence-sdlc/scripts/engine/state.py`:
  - `record_violations` writes `open: false`, `resolved`, `resolved_at` for resolved entries;
  - new `auto_resolved_count`;
  - `_merge` rules for `auto_resolve_max_per_session` (minimum) and `tier3_auto_modes_with_required_gate` (may only become false);
  - `ENGINE_VERSION` becomes 2.2.0.
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`:
  - `_ci_gate` with the signed temp cache, and the `tier3-auto-mode` branch of `check_write` (REQ-LLA-08, 09);
  - `_check_gh` `check-forgery` (REQ-LLA-10).
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`: `_record_transition` judges entries that first appear, and resolved entries become report notes (REQ-LLA-04).
- `plugins/evidence-sdlc/policy/default-policy.json`: the ten new keys, with the spec's defaults.
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`: new `suite_pilot62`, with a case per engine Proof row.
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`: REQ-LLA-04 fixtures in the `verify-range` set.
- `plugins/evidence-sdlc/scripts/tests/fixtures/pilot62/`: `branch-classic.json`, `rules-branch.json`, `repo.json`, captured from this repository in step 1 and trimmed.
- `tests/content_acceptance_tests.py`: REQ-LLA-11.
- Docs and release (REQ-LLA-11):
  - `docs/gates-reference.md`: restored violations, the cap, config edits, Tier 3 auto modes and `check-forgery`;
  - `docs/policy-reference.md`: the new keys and their merge rules;
  - `docs/managed-settings.md`: the owner actions (pin the check to GitHub Actions, `approval.github_repo`, a root-owned org policy, remove permission-mode loosening);
  - `governance/control-mapping.md`, `governance/supplier-audit-packet.md` and `SECURITY.md`: the monitor is detection with verified automatic undo, and unresolved violations still block;
  - `HANDOFF.md`;
  - `CHANGELOG.md` `## 2.2.0`, with Known issues (PILOT-63 release automation);
  - versions 2.2.0 in `plugins/evidence-sdlc/.claude-plugin/plugin.json`, `plugins/evidence-discovery/.claude-plugin/plugin.json`, `plugins/evidence-quality/.claude-plugin/plugin.json`, `plugins/evidence-compliance/.claude-plugin/plugin.json`, `plugins/evidence-integrations/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
- `.evidence/decisions/0005-local-layer-is-advisory-behind-the-server-gate.md` (new; written with this plan).

## Order of work
1. Write the failing tests for every Proof row, and run them to record why each fails.
   - Capture the fixtures. **Human step:** the owner runs, in their own terminal:
     - `gh api repos/<repo>/branches/main`
     - `gh api repos/<repo>/rules/branches/main`
     - `gh api repos/<repo>`

     Then they paste the output, or save it to `plugins/evidence-sdlc/scripts/tests/fixtures/pilot62/`.
   - Confirm the `checks[].app_id` field and the GitHub Actions app id against the capture.
   - `grep` the engine tests for cases asserting a push or edit denial after a *restored* change, and list them here.
2. **Engine helpers before callers** (hooks read the engine live; a NameError locks the session out):
   - add `AUTO_RESOLVABLE`, `st.auto_resolved_count`, the `resolved` fields in `record_violations`, `_local_settings_change`, `_not_user_writable`, `_claude_json_projection` and `_ci_gate`, each unused;
   - run the engine suite (background, about 8 minutes).
3. REQ-LLA-01, 02, 03: the verified undo in `integrity.check`, and the split and cap in `hook.run_integrity`. Run the engine suite.
4. REQ-LLA-05, 06, 07: `settings.local.json` classification, and system and `~/.claude.json` handling in `_extras` / `check`. Run the engine suite.
5. **CHECKPOINT:** re-read spec.md and ADR-0005.
   - Run the full engine suite: every existing case passes, or is listed in step 1 with the reason.
   - Run `evidence audit verify` on this repository's logs.
   - Then run the **security-reviewer on steps 3–4 alone**, and wait for it to finish.
6. REQ-LLA-08, 09, 10: the `_ci_gate` wiring in `check_write`, and `check-forgery` in `_check_gh`. Add the policy keys to `default-policy.json` and the `_merge` rules.
   - **Precondition:** the human has resolved the uncommitted working-tree edit of `default-policy.json` and removed `default-policy.json.bak`. If not, stop and ask. Never stage, overwrite or revert them.
7. REQ-LLA-04: `_record_transition`, with the `verify-range` fixtures (`cli-lifecycle-tests.py verify-range`).
8. REQ-LLA-11: docs, governance, SECURITY, HANDOFF, CHANGELOG, versions.
9. Run the engine, lifecycle, `verify-range` fixture and content suites directly (no `JUNIT_OUT`). Confirm nothing under `validation/` changed.
10. Reviewers one at a time, with no edits during a run: code-reviewer, security-reviewer, then the verifier last. Only a new Critical or High reopens the code; everything else is listed for PILOT-59/60/63.
11. Commit and push. The maintainer opens the PR from their own account; Harshil reviews; the human merges and releases.

    **Owner actions after the merge:**
    - in branch protection on `main`, make `verify-range` required **and set its source to GitHub Actions**;
    - set `approval.github_repo` in the org policy;
    - recreate the org policy root-owned if it is not;
    - remove the org policy's permission-mode loosening once MAN-LLA-01 passes.

Steps 3–4 and step 7 are independent after step 2.

## Mid-flight checkpoint (Tier 2/3)
Step 5.

## Reuse decisions
- Restores reuse the existing snapshot and `st.write_file` / `remove_file`. Only the re-read is new.
- The "closed" state reuses the violations record and `open` flag, so `open_violations`, `_review_gate` and `check_write` need no change.
- `settings.local.json` handling extends the B4 `_permission_grant` parse, keeping its strict UTF-8 and BOM rules.
- Gate detection uses `st.run_gh` (pinned repository, scrubbed environment), so the REQ-IMH-22 subprocess allow-list is unchanged. The cache uses the snapshot's no-follow temp-file helpers and `signing`.
- Rule 5 extends `_record_transition` and does not add a rule.

## Risks
- **Step 3 can lock this session** (hooks read `integrity.py` and `hook.py` live). Mitigation: helpers first, small edits, the engine suite after each step. Rollback: `git checkout -- <file>` by the human.
- **An over-broad exemption** would let an agent persist a hook or an MCP server. Mitigation: the keep-list is an allow-list, not a deny-list, and each command-running key has its own negative test.
- **Gate detection latency.** Up to two `gh` calls (10 s timeout each) inside a 25-second hook budget, on a cache miss only. A timeout fails closed (deny), never open.
- **The fixture shape differs from the real API** [NEEDS VERIFICATION]: step 1 captures real responses.
- **Size:** estimate 600–900 changed lines [NEEDS VERIFICATION after step 1].

## Proof

| REQ ID | Requirement | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-LLA-01 | A verified restore or removal is closed at birth, logged, and blocks neither push nor edits | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-01 …" (restored `approval.json`; removed new control-plane file; removed planted symlink; push and edit then allowed) | CI engine.xml |
| REQ-LLA-02 | Negative: everything not verifiably undone stays open and blocks | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-02 …" (unsigned; restore write fails; re-read mismatch; unclaimed source file by an unparsed program; audit truncation; each → push denied) | CI engine.xml |
| REQ-LLA-03 | The per-session cap reopens auto-resolution; 0 disables it; a repo may only lower it | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-03 …" | CI engine.xml |
| REQ-LLA-04 | `verify-range` rule 5 accepts closed-at-birth `restored` entries with a note, and fails other closed-at-birth entries without `cleared_by` | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-LLA-04 …" (stubbed API, test key) | CI lifecycle.xml |
| REQ-LLA-05 | `settings.local.json`: grants and tightening are kept and logged; command-running keys, deny/ask removals, invalid JSON and a BOM are restored | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-05 …" (allow removed; directory added; `hooks`; `disableAllHooks`; `env`; `enabledPlugins`; deny removed; BOM) | CI engine.xml |
| REQ-LLA-06 | A system config file the user cannot write is logged, not charged; a user-writable one is still `hidden-change` | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-06 …" | CI engine.xml |
| REQ-LLA-07 | `~/.claude.json` is charged only on MCP or tool-permission changes, or on becoming invalid | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-07 …" (scratch `HOME`) | CI engine.xml |
| REQ-LLA-08 | Tier 3 `auto` and `acceptEdits` are allowed when the gate is confirmed; `bypassPermissions`, unsigned, flag off and repo-loosened cases are denied | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-08 …" (fake `gh`) | CI engine.xml |
| REQ-LLA-09 | Gate detection: required and pinned to GitHub Actions (classic or ruleset) confirms; any-source, other app, missing, `gh` failure, non-JSON or empty repo does not; the signed cache is honoured, and an altered or expired one is not | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-09 …" (fake `gh`, fixtures under `fixtures/pilot62/`) | CI engine.xml |
| REQ-LLA-10 | Creating a commit status or check run with `gh api` is denied as `check-forgery`; reading one is allowed | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-LLA-10 …" | CI engine.xml |
| REQ-LLA-11 | Docs, governance, SECURITY, HANDOFF, CHANGELOG 2.2.0 and versions match; owner actions and the release-automation deferral are stated | content | yes | — | `tests/content_acceptance_tests.py` "REQ-LLA-11 …" | CI content.xml |
| REQ-LLA-08 (live) | Live, on this machine after the owner actions: with the org policy's permission-mode loosening removed, a Tier 3 edit in `auto` mode is allowed. With `verify-range` set to "any source" in branch protection, the same edit is denied, naming the pin | manual | no | MAN-LLA-01 | — | Session audit log excerpt in the release note |

## Considered and rejected
- **An owner-set "gate is required" policy flag,** and a repository flag (see spec, "Rejected alternatives").
- **Release automation in CI on merge.** It needs writes to protected `main` from CI and a human-authored workflow. It is deferred to PILOT-63 (spec, "Out of scope").
- **Accepting signed record changes mid-call** (a human's clear or approval during a call). This is PILOT-59.
