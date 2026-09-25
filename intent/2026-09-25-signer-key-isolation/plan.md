# Plan: Signer key isolation — a separate-user signer that never runs git, typed records, a human channel, key IDs
Tracker: PILOT-61   From: intent/2026-09-25-signer-key-isolation/spec.md   Date: 2026-09-25
Risk tier: 3 — the change moves custody of the key behind every signed record, changes what the hooks do when signing fails (fail closed for every tool), reroutes every human-only action, and tightens `verify-range` rules 0, 4 and 5. It adds a root-installed daemon and one new subprocess site. "Any change to this framework's own gates" is Tier 3 (risk-tiering skill), and `**/audit/**` floors there. A mistake either locks every session out or lets an agent forge approvals. A second human approves (Harshil).

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

Written with evidence-sdlc disabled in `.claude/settings.json` (owner decision, 2026-09-25): no change state exists for PILOT-61 yet, and nothing here is signed. The human runs `evidence change start PILOT-61 --tier 3 --kind fix` before approving.

## Files claimed
- `intent/2026-09-25-signer-key-isolation/**`
- `.evidence/decisions/**`
- `plugins/evidence-sdlc/signer/evidence_signer.py` (new)
- `plugins/evidence-sdlc/signer/install.sh` (new)
- `plugins/evidence-sdlc/signer/com.evidence-chain.signer.plist` (new)
- `plugins/evidence-sdlc/signer/evidence-signer.service` (new)
- `plugins/evidence-sdlc/scripts/engine/signing.py`
- `plugins/evidence-sdlc/scripts/engine/state.py`
- `plugins/evidence-sdlc/scripts/engine/integrity.py`
- `plugins/evidence-sdlc/scripts/engine/hook.py`
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
- `plugins/evidence-sdlc/scripts/cli/evidence_trace.py`
- `plugins/evidence-sdlc/policy/default-policy.json`
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`
- `plugins/evidence-sdlc/scripts/tests/signer-tests.py` (new)
- `plugins/evidence-sdlc/scripts/tests/fixtures/pilot61/**` (new: test keyrings, legacy-signed records, verify-range fixtures)
- `scripts/ci/run-tests.sh`
- `tests/content_acceptance_tests.py`
- `managed-settings.json`
- `docs/managed-settings.md`
- `docs/gates-reference.md`
- `docs/policy-reference.md`
- `governance/control-mapping.md`
- `governance/supplier-audit-packet.md`
- `governance/records-retention.md`
- `SECURITY.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `plugins/*/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

Not changed: `.github/workflows/**` (the secret's value changes, not its name or the files), `pipelines/**`, `validation/**`, `plugins/evidence-sdlc/scripts/engine/cmdparse.py`, `plugins/evidence-sdlc/scripts/engine/monitor.py` (PILOT-59's; its callers pass `rt`, see "Coordination"), `plugins/evidence-sdlc/hooks/hooks.json`, `.claude/settings.json`.

## Files that change
- `plugins/evidence-sdlc/signer/evidence_signer.py` (new, standard library only; REQ-KEY-01..05, 11):
  - `main` with the subcommands `serve`, `confirm`, `rotate`, `retire`, `info`, and `--test-root <dir>`;
  - `_check_layout` (REQ-KEY-02), `_peer_uid` (Linux `SO_PEERCRED`, macOS `LOCAL_PEERCRED`), `_strict_json`, `SCHEMAS` per `rt`, `_canon`, `_mac`;
  - `SignerState` (audit heads, last state per change, violation entries, the per-session `restored` count, sealed `(repo, session, tool_use_id)` identities), stored under `<keyring dir>/state/` with `os.open(O_NOFOLLOW)` and atomic renames;
  - `_serve_agent` (Class A) and `_serve_human` (Class H, uid 0), a rate limiter, and a `SIGHUP` keyring reload.
- `plugins/evidence-sdlc/signer/install.sh` (new): creates the user, the root-owned `/usr/local/libexec/evidence-signer/`, the keyring and its directory, the socket directory, and the unit; `--uninstall`. It prints no key.
- `plugins/evidence-sdlc/signer/com.evidence-chain.signer.plist` and `evidence-signer.service` (new).
- `plugins/evidence-sdlc/scripts/engine/signing.py`:
  - `init(context, policy)`, the backends `_SignerBackend` (socket client) and `_EnvBackend` (keyring or raw key, CLI only);
  - `sign(rt, obj)`, `verify(rt, obj)`, `verify_many`, `enabled()` (REQ-KEY-04, 08, 09);
  - `human_sign` and `_sudo_confirm`, the one new subprocess site (REQ-KEY-06, 14);
  - `SignerUnavailable`.
- `plugins/evidence-sdlc/scripts/engine/state.py`:
  - `_child_env` also removes `EVIDENCE_SIGNING_KEYS` (REQ-KEY-08);
  - `rt` passed at `save_state`, `write_violations`, `_read_violations`, `_open_log`, `audit_append`, `audit_verify_lines` (with `verify_many` and the legacy-prefix rule, REQ-KEY-12), `approval_problem` (the `channel` rule, REQ-KEY-07), `recorded_agents`;
  - `_merge` rules for `signer` (REQ-KEY-10);
  - `ENGINE_VERSION` becomes 2.5.0 (2.6.0 if PILOT-59 splits).
- `plugins/evidence-sdlc/scripts/engine/integrity.py`: `snapshot` and `check` pass `rt: snapshot`; `check`'s `signed = signing.enabled()` is true in signer mode even when the signer is down (REQ-KEY-09).
- `plugins/evidence-sdlc/scripts/engine/hook.py`:
  - `main`: `signing.init("hook", policy)` first, removing both key variables (REQ-KEY-08);
  - `run_pre`: `signing-key-in-hook-env`, `signer-unavailable`, `signer-misconfigured` denials, and the pending-marker check (REQ-KEY-08, 09, 10);
  - `run_post`: the unsigned marker when signing fails (REQ-KEY-09);
  - `run_session_start`: the signer line, and no UNSIGNED MODE text in signer mode;
  - `run_lifecycle`: docstring (the hook no longer holds a key).
- `plugins/evidence-sdlc/scripts/engine/lifecycle.py`:
  - `_require_key_if_signed`: unchanged in `off` mode; in signer mode it is replaced by `signing.human_sign`;
  - `cmd_change` (`set-tier`, `release`, `override`), `_clear_violations`, `write_approval` (a `channel` argument), `cmd_approve`, `_approve_github`, `approve_from_prompt` (`channel: agent`, REQ-KEY-07);
  - a new `evidence signer migrate` and `evidence signer status` in `register` / `main` (REQ-KEY-12);
  - `_verify_pr` and `_verify_push` rule 0 (the keyring form of the secret), `_check_audit` (rule 4) and `_check_records` (rule 5): the legacy-kid rule when the base policy is in signer mode (REQ-KEY-12).
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`: `check_gated` and `_log_tail_only` pass `rt` and apply the `channel` rule; `check_bash`: `signer-access` next to the existing key-name regex at `:813` (REQ-KEY-15).
- `plugins/evidence-sdlc/scripts/cli/evidence_trace.py`: `_signing` (the CLI context), `cmd_results` (`rt: result`, the `ci` kid, the raw-key warning) and `result_sidecar_ok` (REQ-KEY-13).
- `plugins/evidence-sdlc/policy/default-policy.json`: the `signer` object with the spec's defaults.
- `plugins/evidence-sdlc/scripts/tests/signer-tests.py` (new): the signer suite, run against `--test-root` instances with generated test keys.
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`: new `suite_pilot61`, and the REQ-IMH-22 `allowed` set gains `signing.py:_sudo_confirm` (REQ-KEY-14).
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`: `verify_range_61_tests()` and `results_61_tests()`.
- `plugins/evidence-sdlc/scripts/tests/fixtures/pilot61/`: `keys-test.json`, `keys-rotated.json`, `legacy-approval.json`, `legacy-audit.jsonl`, and the verify-range fixture repositories' scripts.
- `scripts/ci/run-tests.sh`: runs `signer-tests.py` as a suite, and passes the test keyring only through the fixture path (still `env -u EVIDENCE_SIGNING_KEY` for every suite).
- `tests/content_acceptance_tests.py`: REQ-KEY-02 (the installer's modes), REQ-KEY-15 (the template), REQ-KEY-16.
- `managed-settings.json` (template): the key removed from `env`, the `envVars` deny kept, sandbox and Read denies for the keyring and socket directories, `Bash(sudo *)` in `permissions.deny`, and the `_comment` step (5) rewritten.
- Docs and release (REQ-KEY-16):
  - `docs/managed-settings.md`: "Signing key" rewritten as "Signer": install, the owner checklist, the `sudo` prerequisite, rotation, cutover, and the CI secret. The key-pasting one-liner is removed;
  - `docs/gates-reference.md`: record classes, channels and the new denials;
  - `docs/policy-reference.md`: the `signer` keys and their merge rules;
  - `governance/control-mapping.md`, `governance/supplier-audit-packet.md`, `governance/records-retention.md` and `SECURITY.md`: key custody, separation of duties, and the new residual;
  - `HANDOFF.md`;
  - `CHANGELOG.md` `## 2.5.0` (or `## 2.6.0`);
  - versions in `plugins/evidence-sdlc/.claude-plugin/plugin.json`, `plugins/evidence-discovery/.claude-plugin/plugin.json`, `plugins/evidence-quality/.claude-plugin/plugin.json`, `plugins/evidence-compliance/.claude-plugin/plugin.json`, `plugins/evidence-integrations/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
- `.evidence/decisions/0007-signing-key-held-by-a-separate-user-signer.md` (new; written with this plan). `.evidence/decisions/0003-hook-git-is-neutralised.md`: a dated revision note to §4 in step 10.

## Coordination
**Merge order: PILOT-62 → PILOT-60 → PILOT-59 → PILOT-61, with a rebase onto `main` after each merge.**
- PILOT-62 (`feat/PILOT-62-local-layer-advisory`, plan at `61667a2`) ships 2.2.0.
- PILOT-60 (`fix/PILOT-60-usability`, plan at `a14382c`) ships 2.3.0.
- PILOT-59 (`fix/PILOT-59-concurrency-and-deferrals`, plan at `d495f36`) ships 2.4.0, or 2.4.0 (59b) and 2.5.0 (59a) if split.
- **PILOT-61 ships 2.5.0, or 2.6.0 if PILOT-59 splits.** If the owner reorders the merges, the change that merges later takes the higher version.

**Before PILOT-59 merges,** PILOT-61 does only work in files no other change claims:
- `signer/**` (the daemon, installer and units) and `signer-tests.py`;
- `fixtures/pilot61/**`;
- ADR-0007.

The signer's `SCHEMAS` for PILOT-59's `lease`, `seq`, `last-post` and `attestation` records are written from ADR-0006 and PILOT-59's spec, and confirmed against the merged code after the rebase.

**PILOT-59's records call the signer.** After the rebase:
- every `signing.sign` / `verify` call PILOT-59 adds (`monitor.py` leases, `seq`, `last-post`; `st.attested_write` attestations) gains its `rt`. That is a one-argument edit in PILOT-59's code, made in this change;
- the signed lease and `seq` are Class A with first-write-wins per `(repo, session, tool_use_id)` (REQ-KEY-05);
- a human action's attestation is signed in the same `human.sock` request as its record (REQ-KEY-06), so PILOT-59's "attested human writes stand mid-call" keeps working;
- ADR-0006's forgery argument ("the agent has no key") becomes true by construction in signer mode.

**Shared files, and the functions each change edits:**

| File | PILOT-62 edits | PILOT-60 edits | PILOT-59 edits | PILOT-61 edits |
| --- | --- | --- | --- | --- |
| `signing.py` | none | none | none (explicitly not changed) | the whole module |
| `state.py` | `record_violations`, new `auto_resolved_count`, two `_merge` rules, `ENGINE_VERSION` | `check_git_config`, new `ENGINE_ALWAYS_REFUSED` / `_engine_ignored`, one `_merge` rule, `ENGINE_VERSION` | `_dir_fd`, `write_file`, new `attested_write`, `save_state`, `write_violations`, `record_violations`, `audit_verify_lines`, `_attr_source`, `current_branch`, four `_merge` rules, `ENGINE_VERSION` | `_child_env`, `save_state` (**same as PILOT-59**), `write_violations` (**same as PILOT-59**), `_read_violations`, `_open_log`, `audit_append`, `audit_verify_lines` (**same as PILOT-59**), `approval_problem`, `recorded_agents`, new `attested_write` call (`rt` only), one `_merge` rule, `ENGINE_VERSION`. **Not** `check_git_config` or `run_git` |
| `integrity.py` | `check` step 1 / 1a, `_permission_grant` → `_local_settings_change`, `_extras`, new helpers | none | `_snap_rel` / `_snap_path`, `snapshot`, the `check` preamble and steps 1 and 3, `_hash`, `_dirty`, `_git_dir_id`, `_extras` | `snapshot` (the `sign` call, **same function as PILOT-59**), `check` (the `verify` call in the preamble and `signed =`, **same function as PILOT-62 and PILOT-59**) |
| `hook.py` | `run_integrity` | none | `run_pre`, `run_post`, `run_integrity` | `main`, `run_pre` (**same as PILOT-59**: new denials before its lock), `run_post` (**same as PILOT-59**), `run_session_start`, `run_lifecycle` docstring. **Not** `run_integrity` |
| `lifecycle.py` | `_record_transition` | none | `write_approval`, `_clear_violations`, `cmd_change`, `approve_from_prompt`, `_approve_github`, `_check_audit`, `_check_paths`, `_owners_of` | `_require_key_if_signed`, `write_approval`, `_clear_violations`, `cmd_change`, `cmd_approve`, `approve_from_prompt`, `_approve_github` (**all but `cmd_approve` same as PILOT-59**), `_check_audit` (**same as PILOT-59**), `_check_records`, `_verify_pr`, `_verify_push`, `register`, `main`. **Not** `_record_transition` |
| `evidence_policy.py` | `check_write` `tier3-auto-mode` branch, `_check_gh`, new `_ci_gate` | `check_bash` argument loop, `_check_script`, new temp helpers | `check_write` `tier3-same-person` branch, a new advisory note, `_commit_bypass`, the commit-message fallback | `check_gated`, `_log_tail_only`, `check_bash` (the key-name regex at its top, **same function as PILOT-60**, a different block) |
| `evidence_trace.py` | none | `_strip_comment`, `load_adapter`, `find_eval_covers`, `build_graph`, `register_gaps`, `cmd_gaps` | none | `_signing`, `cmd_results`, `result_sidecar_ok` |
| `default-policy.json` | ten new keys | `git_config_engine_ignored` | four new keys | the `signer` object |
| `engine-tests.py` | `suite_pilot62` | harness (`case`, `SUITES`, `--suite`), `suite_pilot60` | `suite_pilot59` | `suite_pilot61` (on PILOT-60's harness), the REQ-IMH-22 `allowed` set |
| `cli-lifecycle-tests.py` | `verify-range` fixtures (REQ-LLA-04) | `gaps_tests()` | `verify_range_59_tests()`, `approve_github_59_tests()` | `verify_range_61_tests()`, `results_61_tests()` |
| `scripts/ci/run-tests.sh` | none | `EVIDENCE_RESULTS_DIR`, stale-file clearing, the final self-check step | none | one new suite line, before PILOT-60's self-check step |
| `.evidence/decisions/0003-*.md` | none | a revision note to §2 | none | a revision note to §4 |
| docs, governance, SECURITY, HANDOFF, CHANGELOG, versions | 2.2.0 | 2.3.0 | 2.4.0 (or 2.4.0 / 2.5.0) | 2.5.0 (or 2.6.0) |

**Composition rules after the rebase:**
1. **PILOT-62's per-session `restored` cap** is also enforced by the signer (REQ-KEY-05). The engine's count and the signer's count must agree; a test drives both to the cap.
2. **PILOT-62's `_ci_gate` cache** is Class A, `rt: ci-gate`. It stays a signed file in the temp directory.
3. **PILOT-60's `check_git_config` exemptions** still matter, because hooks still run git. In signer mode, a refused config no longer protects a key; it protects Class A integrity and the correctness of the monitor. PILOT-61 does not touch that function.
4. **PILOT-59's attestations** are Class A for agent-channel records and are signed with the record for human-channel ones.
5. Rebase conflicts are expected in `state.py` (the four shared functions), `integrity.snapshot` / `check`, `hook.run_pre` / `run_post`, the six shared `lifecycle.py` functions, `default-policy.json`, the `SUITES` list, `run-tests.sh` and the docs. Resolve them by keeping every side's behaviour, then rerun all four changes' suites.

## Order of work
1. **Verify and write the failing tests.**
   - Confirm `socket.SO_PEERCRED` on Linux (the CI runner) and `socket.LOCAL_PEERCRED` on macOS with Python 3.8 and 3.14 (3.14.7 on this machine: `LOCAL_PEERCRED` = 1, checked).
   - Confirm from Claude Code's settings documentation the sandbox keys the template relies on: `sandbox.network.allowUnixSockets`, `allowUnsandboxedCommands`, and whether hooks inherit the sandbox (they do not today, per `signing.py`'s docstring) [NEEDS VERIFICATION].
   - Confirm on both platforms that a process of another uid cannot read the signer's environment or memory without root, and that `sudo` with the default `tty_tickets` does not carry a ticket into a process with no terminal. Record the results here.
   - Write every Proof row's test and run it to record why it fails. Engine cases go in `suite_pilot61` after the PILOT-60 rebase; before it, they go in `signer-tests.py` or a scratch file.
2. **Signer first, before PILOT-59 merges** (files no one else claims):
   - `evidence_signer.py` with `--test-root`, the schemas, `SignerState`, `rotate` / `retire`;
   - `install.sh` and the two units;
   - run `signer-tests.py`.
3. **CHECKPOINT (signer):**
   - re-read spec.md and ADR-0007;
   - run the **security-reviewer on the signer alone** (steps 1–2), and wait for it to finish.
4. **After PILOT-59 merges, rebase.** Then, **engine helpers before callers** (hooks read the engine live; a NameError locks the session out):
   - add the new `signing` API alongside the old one (`sign(obj)` keeps working, with `rt` inferred from a keyword default) and `human_sign`, each unused;
   - run the engine suite (background, about 8 minutes).
5. REQ-KEY-04, 08, 09, 10: `signing.init` in `hook.main`, the backends, the new denials in `run_pre` / `run_post`, and every caller passing `rt` (state, integrity, evidence_policy, PILOT-59's `monitor.py` callers). Run the engine suite after each file.
6. REQ-KEY-06, 07, 12, 14: the human channel in `lifecycle.py`, the `channel` rule, `evidence signer migrate`, and the AST allow-list update. Run the engine and lifecycle suites. Measure the hook latency with a test signer, and record it here (spec, "Areas of concern").
7. REQ-KEY-10, 13, 15: `default-policy.json` and `_merge`, `evidence_trace.py`, `signer-access`, the `managed-settings.json` template.
   - **Precondition:** the human has resolved the uncommitted working-tree edit of `default-policy.json` and removed `default-policy.json.bak`. If not, stop and ask. Never stage, overwrite or revert them.
8. **CHECKPOINT (engine):**
   - re-read spec.md, ADR-0007 and ADR-0003;
   - run the full engine, lifecycle and signer suites, first with `signer.mode: off` (every existing case unchanged except REQ-IMH-22's set) and then with a test signer in `required` mode;
   - run `evidence audit verify` on this repository's logs;
   - run the **security-reviewer on steps 4–7 alone**, and wait for it to finish.
9. Remove the old one-argument `sign(obj)` / `verify(obj)` once no caller uses it. Run the engine suite.
10. REQ-KEY-16: ADR-0003 revision note, ADR-0007 status note, docs, governance, SECURITY, HANDOFF, CHANGELOG, versions. Run the engine, lifecycle, signer, `verify-range` fixture and content suites directly (no `JUNIT_OUT`). Confirm nothing under `validation/` changed.
11. Reviewers one at a time, with no edits during a run: code-reviewer, security-reviewer, then the verifier last. Only a new Critical or High reopens the code; everything else is listed for a later change.
12. Commit and push (`git add` and `git commit` in separate calls; `-m` flags, no heredoc). The maintainer opens the PR from their own account; Harshil reviews; the human merges and releases.
13. **Live checks after the merge, human-run:** MAN-KEY-01 (macOS install and a session), MAN-KEY-02 (Linux install), MAN-KEY-03 (sandboxed Bash cannot reach `agent.sock`).

    **Owner actions:**
    - run `sudo plugins/evidence-sdlc/signer/install.sh` on each machine, and put the session user's uid and the pinned repository in the keyring (`allowed_uids`, `repos`);
    - put the 2.x key into the keyring as `legacy` (`use: verify`) through `install.sh --import-legacy`, which reads it from a root-only file the owner names, and then **remove `EVIDENCE_SIGNING_KEY` from `managed-settings.json` `env`**;
    - set `signer.mode: required` and `approval.github_repo` in the org policy;
    - run `evidence signer migrate` in a terminal, for each repository;
    - replace the `EVIDENCE_SIGNING_KEY` Actions secret's value with the CI keyring from `sudo evidence-signer rotate --export-ci` (written to a root-only file);
    - confirm `sudo` needs a password per terminal (no `NOPASSWD`, no `timestamp_type=global`);
    - retire `legacy` once every branch opened before the cutover has merged.

Steps 2 and 4 are independent (different files). Steps 5–7 wait for the rebase in step 4.

## Mid-flight checkpoint (Tier 2/3)
Steps 3 and 8.

## Reuse decisions
- **The MAC is unchanged:** HMAC-SHA256 over the same canonical JSON as `signing._canon`, now computed in the signer. Only `rt`, `kid`, `repo` and `channel` are new fields, and they are inside the signed body.
- **Human confirmation** keeps `_human_tty`'s rules (no Claude Code environment, a real `/dev/tty`) and its typed confirmations. Only where the signature comes from changes.
- **Records are still written by the engine** with `st.write_file` (no-follow, atomic). The signer never touches the repository.
- **CI keeps the environment backend,** the same secret name and the same workflows.
- **The subprocess rule** keeps its AST test; the allow-list gains exactly one site, and the signer gets a stricter test with no allow-list.
- **Engine tests** keep using the environment key in `off` mode, so the existing suites prove backwards compatibility unchanged.

## Risks
- **Steps 5–7 can lock this session.** Hooks read `signing.py`, `state.py` and `hook.py` live, and a signing error in signer mode denies every write tool. Mitigation: the old API is kept until step 9; the development session stays in `signer.mode: off`; helpers first, small edits, the engine suite after each step. Rollback: `git checkout -- <file>` by the human.
- **A signer bug denies every call** in signer mode. Mitigation: `signer.mode: off` in the org policy is the documented emergency switch. It restores 2.x behaviour and its stated residual risk, and it needs the root-owned org policy, which the agent cannot write.
- **The installer runs as root.** Mitigation: it is short, it is reviewed as change-controlled code, it writes only the listed paths, and a content test checks its modes. It never downloads anything.
- **A schema that is too strict** refuses a legitimate record and blocks work. Mitigation: the schemas are generated from the records the existing suites write, and step 8 runs every suite in `required` mode.
- **Trust on first use** of audit logs (spec, "Areas of concern").
- **Platform differences** in peer credentials and process inspection [NEEDS VERIFICATION: step 1].
- **Rebase conflicts** with PILOT-62, PILOT-60 and PILOT-59 (see "Coordination").
- **Size:** estimate 1,400–2,000 changed lines, about half of them tests [NEEDS VERIFICATION after step 1]. A split (the signer and installer in one PR, the engine integration in a second) is possible. It is not recommended, because the signer alone changes no behaviour and cannot be reviewed against its callers.

## Proof

| REQ ID | Requirement | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-KEY-01 | The signer starts no program and imports no engine module; negative fixtures with a `subprocess.run` or `import state` fail | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-KEY-01 …" (AST over `signer/*.py`; two negative fixtures under `fixtures/pilot61/`) | CI engine.xml |
| REQ-KEY-02 | The signer refuses an unsafe keyring, directory or code file, and starts on the safe layout; the installer sets the modes and prints no key | signer | yes | — | `plugins/evidence-sdlc/scripts/tests/signer-tests.py` "REQ-KEY-02 …" (`0644` keyring; symlinked keyring; group-writable directory; writable code file; safe layout) and `tests/content_acceptance_tests.py` "REQ-KEY-02 install.sh …" | CI signer.xml, content.xml |
| REQ-KEY-03 | Negative: a peer uid not allowed, Class H on the agent socket, oversize, duplicate keys, `NaN` and over-rate requests are refused; an unanswering socket fails within 6 s | signer | yes | — | `plugins/evidence-sdlc/scripts/tests/signer-tests.py` "REQ-KEY-03 …" | CI signer.xml |
| REQ-KEY-04 | Typed signing: extra keys, long strings, another `rt` and an unknown `repo` are refused or verify false; `info` leaks no key; re-serialised records verify | signer | yes | — | `plugins/evidence-sdlc/scripts/tests/signer-tests.py` "REQ-KEY-04 …" | CI signer.xml |
| REQ-KEY-05 | Negative: an audit fork, a stage moved to `approved` or backwards, a tier change, a violation closed on the agent channel, the cap exceeded and a second snapshot for one `tool_use_id` are refused | signer | yes | — | `plugins/evidence-sdlc/scripts/tests/signer-tests.py` "REQ-KEY-05 …" | CI signer.xml |
| REQ-KEY-06 | Class H goes only through `sudo` and the root-owned helper with a typed confirmation; a wrong confirmation, an unsafe helper and a Claude Code environment are refused | signer | yes | — | `plugins/evidence-sdlc/scripts/tests/signer-tests.py` "REQ-KEY-06 …" (fake `sudo`, pty) and `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-KEY-06 hook-side human_sign refused" | CI signer.xml, engine.xml |
| REQ-KEY-07 | A prompt approval is `channel: agent` and unlocks Tier 1–2 only; Tier 3 needs a `human` approval or GitHub; `off` mode unchanged | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-KEY-07 …" | CI engine.xml |
| REQ-KEY-08 | No hook holds a key: a delivered key denies write tools (`signing-key-in-hook-env`) and is never used; commands' environments have neither variable | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-KEY-08 …" (test signer; environment sentinel; `env > file` command) | CI engine.xml |
| REQ-KEY-09 | Negative: the signer down denies write tools and Bash, `verify` is `False`, no UNSIGNED MODE; an outage mid-call is recorded once the signer is back | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-KEY-09 …" | CI engine.xml |
| REQ-KEY-10 | `signer` policy merges tighten-only; paths from a repository are ignored; required without `github_repo` is denied | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-KEY-10 …" | CI engine.xml |
| REQ-KEY-11 | Rotation and retirement: new kid on new records, old ones verify until retired; non-root rotate refused; the export is `0400` and nothing is printed | signer | yes | — | `plugins/evidence-sdlc/scripts/tests/signer-tests.py` "REQ-KEY-11 …" (`fixtures/pilot61/keys-rotated.json`) | CI signer.xml |
| REQ-KEY-12 | Cutover: legacy records are refused locally until migrated; legacy audit lines only as a prefix; `verify-range` fails legacy records or lines added in the range when the base is in signer mode | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-KEY-12 …" and `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-KEY-12 …" (test keys, `fixtures/pilot61/legacy-*`) | CI engine.xml, lifecycle.xml |
| REQ-KEY-13 | CI signs results with its own kid from a keyring (a raw key is `legacy` with a warning); the local signer refuses `rt: result` and verifies CI sidecars | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-KEY-13 …" and `plugins/evidence-sdlc/scripts/tests/signer-tests.py` "REQ-KEY-13 result sign refused" | CI lifecycle.xml, signer.xml |
| REQ-KEY-14 | The subprocess allow-list is exactly the five sites; a second site in `signing.py` fails; `_sudo_confirm` uses a list argv and a clean environment | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-IMH-22 …" (updated set) and "REQ-KEY-14 …" | CI engine.xml |
| REQ-KEY-15 | Agent commands naming the signer's sockets, helper or keyring are denied `signer-access`; unrelated `/var/run` reads are allowed; the template holds no key | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-KEY-15 …" and `tests/content_acceptance_tests.py` "REQ-KEY-15 managed-settings template …" | CI engine.xml, content.xml |
| REQ-KEY-16 | ADR-0007, the ADR-0003 note, docs, governance, SECURITY, HANDOFF, CHANGELOG 2.5.0 (or 2.6.0) and versions match; owner actions, prerequisites and the residual are stated | content | yes | — | `tests/content_acceptance_tests.py` "REQ-KEY-16 …" | CI content.xml |
| REQ-KEY-02 | Live on macOS after the owner installs: the LaunchDaemon runs as `_evidencesigner`; a session in signer mode signs records with the local kid; `ps eww` on a running hook shows no key | manual | no | MAN-KEY-01 | — | Terminal output (with no key) pasted in the release note |
| REQ-KEY-02 | Live on Linux: the systemd unit runs as `evidence-signer` with `NoNewPrivileges`; `/proc/<hook pid>/environ` has no key | manual | no | MAN-KEY-02 | — | Terminal output pasted in the release note |
| REQ-KEY-03 | Live: a sandboxed Bash call that connects to `agent.sock` fails (the sandbox refuses the socket), while hooks keep signing | manual | no | MAN-KEY-03 | — | Session audit log excerpt in the release note |

## Considered and rejected
- **A same-user signer, a one-shot helper with the key on a file descriptor, a `NOPASSWD` rule, and Ed25519 through `openssl`** (spec, "Rejected alternatives"; ADR-0007).
- **Splitting the signer and the engine integration into two PRs** (see "Risks").
- **Removing prompt approval in signer mode.** Kept for Tier 1–2 pending the owner's decision (REQ-KEY-07).
