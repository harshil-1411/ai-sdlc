# Plan: Usability — CI-owned test results, YAML comments, plan duplicates, temp-directory paths, `-k`, the git config split
Tracker: PILOT-60   From: intent/2026-09-25-usability/spec.md   Date: 2026-09-25
Risk tier: 3 — the gate engine's Bash rules and git config check (the key-holding hook's git, ADR-0003) and where CI signs test evidence (ADR-0002); "any change to this framework's own gates" is Tier 3 (risk-tiering skill), and `.github/workflows/**` floors at 2. A second human approves (Harshil).

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

Written with evidence-sdlc disabled in `.claude/settings.json` (owner decision, 2026-09-25): no change state exists for PILOT-60 yet, and nothing here is signed. The human runs `evidence change start PILOT-60 --tier 3 --kind fix` before approving.

## Files claimed
- `intent/2026-09-25-usability/**`
- `.evidence/decisions/**`
- `.evidence/adapter.example.yml`
- `plugins/evidence-sdlc/scripts/cli/evidence_trace.py`
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`
- `plugins/evidence-sdlc/scripts/engine/state.py`
- `plugins/evidence-sdlc/policy/default-policy.json`
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`
- `plugins/evidence-sdlc/scripts/tests/fixtures/pilot60/**` (new: adapter, spec, plan and JUnit fixtures for the gaps tests)
- `scripts/ci/run-tests.sh`
- `.github/workflows/ci.yml` (human-authored: change-controlled)
- `pipelines/github-actions/evidence-chain.yml`
- `pipelines/gitlab/evidence-chain.gitlab-ci.yml`
- `tests/content_acceptance_tests.py`
- `cli/README.md`
- `docs/gates-reference.md`
- `docs/policy-reference.md`
- `docs/concepts.md`
- `governance/control-mapping.md`
- `governance/supplier-audit-packet.md`
- `CONTRIBUTING.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `plugins/*/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

Not changed: `plugins/evidence-sdlc/scripts/engine/cmdparse.py` (PILOT-59), `integrity.py`, `hook.py`, `lifecycle.py`, `.evidence/adapter.yml`, `validation/**`, `.github/workflows/verify-range.yml`, `plugins/evidence-sdlc/scripts/tests/junit_from_tsv.py` (reused as is), `cli/tests/**`, `.claude/settings.json`.

## Files that change
- `plugins/evidence-sdlc/scripts/cli/evidence_trace.py`:
  - `_strip_comment`, used by `load_adapter` and `find_eval_covers` (REQ-USA-05);
  - `build_graph`: specs before plans, and plan rows that repeat their `From:` spec are references (REQ-USA-06); the `only_results` parameter (REQ-USA-03);
  - `SELF_CHECK_REQUIREMENT`, `--self-check` and `--only-results` in `register_gaps` / `cmd_gaps` (REQ-USA-02, 03).
- `plugins/evidence-sdlc/scripts/engine/evidence_policy.py`: `_TEMP_DATA_PROGS`, `_TEMP_EXEC_OPTS`, `_temp_prefixes`, `_temp_arg_is_data`; the argument loop in `check_bash` and the prefix test in `_check_script` (REQ-USA-07, 08).
- `plugins/evidence-sdlc/scripts/engine/state.py`: `ENGINE_ALWAYS_REFUSED`, `_engine_ignored`, the global/system exemption in `check_git_config`, the `_merge` intersection for `git_config_engine_ignored` (REQ-USA-10, 11); `ENGINE_VERSION` becomes 2.3.0.
- `plugins/evidence-sdlc/policy/default-policy.json`: `git_config_engine_ignored` with the spec's default. `deny_git_config_keys` is unchanged.
- `plugins/evidence-sdlc/scripts/tests/engine-tests.py`:
  - the harness: `case()` runs unselected hooks, `SUITES`, `--suite`, `0 cases matched`, the usage docstring (REQ-USA-09);
  - new `suite_pilot60`, with a case per engine Proof row (REQ-USA-07..11).
- `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py`: new `gaps_tests()` (REQ-USA-02, 03, 05, 06), run by `main()` and alone with the argument `gaps`.
- `plugins/evidence-sdlc/scripts/tests/fixtures/pilot60/`: `adapter-comments.yml`, `spec.md`, `plan-ref.md`, `plan-other.md`, `pass.xml`.
- `scripts/ci/run-tests.sh`: `EVIDENCE_RESULTS_DIR` and the out-of-tree default, clearing stale files, and the final self-check step (REQ-USA-01, 02).
- `tests/content_acceptance_tests.py`: REQ-V2C-09's in-suite check removed; checks for REQ-USA-01, 02, 04 and 12.
- `.github/workflows/ci.yml` (**the human applies**; step 7 has the exact diff), and `pipelines/github-actions/evidence-chain.yml`, `pipelines/gitlab/evidence-chain.gitlab-ci.yml` (REQ-USA-04).
- `.evidence/decisions/0002-ci-owns-test-results.md`: revision 2, written with this plan. `0003-hook-git-is-neutralised.md`: a dated revision note to §2 in step 8.
- Docs and release (REQ-USA-12):
  - `cli/README.md`: `--self-check`, `--only-results`, the comment rule, plan references under `DUPLICATE-ID`;
  - `.evidence/adapter.example.yml`: the comment rule in the header;
  - `docs/gates-reference.md`: temp-directory paths (the `opaque-write` row), the sandbox-safe `mktemp` form, `git-config-refused` and the two sets;
  - `docs/policy-reference.md`: `git_config_engine_ignored` (merge: intersection), `ENGINE_ALWAYS_REFUSED`, and the known-issue sentence under `deny_git_config_keys` removed;
  - `docs/concepts.md`: `DUPLICATE-ID` and plan references;
  - `governance/control-mapping.md` (PW.8, CC8.1 evidence) and `governance/supplier-audit-packet.md`: signed CI artifacts are the test evidence;
  - `CONTRIBUTING.md` and `HANDOFF.md` (`:49` and `:140`): one `run-tests.sh` run, `--results <dir>`, `--suite`;
  - `CHANGELOG.md` `## 2.3.0`, with Known issues (PILOT-64 proposal: re-approval history, `CLAUDE_CONFIG_DIR`);
  - versions 2.3.0 in `plugins/evidence-sdlc/.claude-plugin/plugin.json`, `plugins/evidence-discovery/.claude-plugin/plugin.json`, `plugins/evidence-quality/.claude-plugin/plugin.json`, `plugins/evidence-compliance/.claude-plugin/plugin.json`, `plugins/evidence-integrations/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.

## Coordination with PILOT-62
PILOT-62 (`feat/PILOT-62-local-layer-advisory`, plan at `61667a2`) claims `integrity.py`, `hook.py`, `evidence_policy.py`, `state.py`, `lifecycle.py`, `default-policy.json`, `engine-tests.py`, `cli-lifecycle-tests.py`, `content_acceptance_tests.py`, `docs/gates-reference.md`, `docs/policy-reference.md`, `governance/*`, `SECURITY.md`, `HANDOFF.md`, `CHANGELOG.md` and the versions. The overlap is unavoidable. The rules:

1. **PILOT-62 merges first; PILOT-60 rebases onto `main` after that merge.** Until then, PILOT-60 does only the steps that touch files PILOT-62 does not claim (steps 1–3: `evidence_trace.py`, `run-tests.sh`, `pipelines/**`, fixtures, `cli/README.md`, `.evidence/adapter.example.yml`). Its `cli-lifecycle-tests.py` edit is confined to a new `gaps_tests()` function and one line in `main()`.
2. **Shared files, different functions:**

   | File | PILOT-62 edits | PILOT-60 edits |
   | --- | --- | --- |
   | `evidence_policy.py` | `check_write` (Tier 3 modes), `_check_gh`, new `_ci_gate` | `check_bash` argument loop, `_check_script` prefix test, new temp helpers |
   | `state.py` | `record_violations`, new `auto_resolved_count`, two `_merge` rules | `check_git_config`, new `ENGINE_ALWAYS_REFUSED` / `_engine_ignored`, one `_merge` rule |
   | `default-policy.json` | ten new keys | one new key |
   | `engine-tests.py` | new `suite_pilot62` | harness (`case`, `__main__`), new `suite_pilot60` |

   Rebase conflicts are expected only in `_merge`, the `__main__` suite list, `default-policy.json` and the docs. Resolve them by keeping both sides.
3. **Versions and engine version:** PILOT-62 ships 2.2.0; PILOT-60 ships **2.3.0** (`ENGINE_VERSION`, all plugin.json files, marketplace.json, `CHANGELOG ## 2.3.0` above `## 2.2.0`). If the owner reorders the merges, the change that merges second takes the higher version, and the other rebases.
4. **`deny_git_config_keys`:** PILOT-62's spec defers the split to PILOT-60, so PILOT-62 must not touch that key or `check_git_config`.
5. **After the rebase,** rerun the full engine, lifecycle and content suites before the reviews (step 9). A PILOT-62 test that PILOT-60 changes (none expected) is listed in the PR.

## Order of work
1. **Tests first, for the PILOT-60-only files.** Write the failing CLI tests (`gaps_tests()`, fixtures under `fixtures/pilot60/`) and the content checks for REQ-USA-01, 02 and 04, and record why each fails.
   - Confirm with a scratch repository whether `log.showSignature=true` makes `git log` run `gpg.program`. Record the result in the PR; `gpg.*` stays refused either way.
   - `grep` the engine and content tests for cases asserting a denial of a temp-directory data command or a global alias, and list them here.
   - Confirm `junit_from_tsv.py`'s input format (`pass|fail<TAB>label`) against `template-sensor-tests.sh:235`.
2. REQ-USA-05, 06, 03, 02 in `evidence_trace.py`. Run `cli-lifecycle-tests.py gaps`, `bash cli/tests/test_cli_fixtures.sh` (fixtures 12 and 14 must pass unchanged), and `evidence gaps` on this repository (REQ-P54-07 still passes).
3. REQ-USA-01, 02 in `run-tests.sh`; REQ-USA-04 in `pipelines/**`. The **human** runs `bash scripts/ci/run-tests.sh` once in their own terminal (MAN-USA-01) and pastes the last ten lines and `git status --short`.
4. **Wait for PILOT-62 to merge, then rebase** (see "Coordination with PILOT-62"). Then, **engine helpers before callers** (hooks read the engine live; a NameError locks the session out):
   - add `ENGINE_ALWAYS_REFUSED`, `_engine_ignored`, `_TEMP_DATA_PROGS`, `_TEMP_EXEC_OPTS`, `_temp_prefixes` and `_temp_arg_is_data`, each unused;
   - write `suite_pilot60`'s failing cases and the harness tests (REQ-USA-07..11), and run them with `--suite suite_pilot60` once the harness change is in.
5. REQ-USA-09 (harness), then REQ-USA-07, 08 (the `check_bash` loop), then REQ-USA-10, 11 (`check_git_config`, `_merge`, `default-policy.json`). Run the engine suite after each (background, about 8 minutes).
   - **Precondition:** the human has resolved the uncommitted working-tree edit of `default-policy.json` and removed `default-policy.json.bak`. If not, stop and ask. Never stage, overwrite or revert them.
6. **CHECKPOINT:** re-read spec.md, ADR-0002 and ADR-0003.
   - Run the full engine suite: every existing case passes, or is listed in step 1 with the reason.
   - Then run the **security-reviewer on steps 4–5 alone**, and wait for it to finish.
7. **Human step — `.github/workflows/ci.yml`** (change-controlled). The agent puts this diff in the PR description; the human applies and commits it on the branch:
   - `checks`, the "All suites" step: add `env: EVIDENCE_RESULTS_DIR: ${{ runner.temp }}/results`; the `upload-artifact` step: `if: always()` and `path: ${{ runner.temp }}/results/`.
   - `sign-and-gate`, `download-artifact`: `path: ${{ runner.temp }}/results/`.
   - "Sign this run's results": `python3 ../trusted/plugins/evidence-sdlc/bin/evidence results sign "$RUNNER_TEMP"/results/*.xml`.
   - "Traceability gaps": `if python3 ../trusted/plugins/evidence-sdlc/bin/evidence gaps --help | grep -q -- --only-results; then python3 ../trusted/plugins/evidence-sdlc/bin/evidence gaps --strict --only-results --results "$RUNNER_TEMP/results"; else python3 ../trusted/plugins/evidence-sdlc/bin/evidence gaps --strict --results "$RUNNER_TEMP/results"; fi`.
   - If the owner chose the follow-up option at approval instead, this step moves after the merge, and REQ-USA-04's `ci.yml` content check is added then.
8. REQ-USA-12: ADR-0003 note, docs, governance, CONTRIBUTING, HANDOFF, CHANGELOG, versions.
9. Run the engine, lifecycle (`cli-lifecycle-tests.py`, `… verify-range`, `… gaps`), CLI fixture and content suites directly. Then run `bash scripts/ci/run-tests.sh` as the agent. After REQ-USA-01 this is allowed, because it writes nothing under the working tree. Confirm with `git status` that nothing under `validation/` changed.
10. Reviewers one at a time, with no edits during a run: code-reviewer, security-reviewer, then the verifier last. Only a new Critical or High reopens the code; everything else is listed for PILOT-59/61/64.
11. Commit and push (`git add` and `git commit` in separate calls; `-m` flags, no heredoc). The maintainer opens the PR from their own account; Harshil reviews; the human merges and releases.

    **Owner actions after the merge:**
    - confirm the first `main` CI run signs files under `$RUNNER_TEMP` and `sign-and-gate` passes (MAN-USA-02);
    - remove any org `git_allowed_config` entries that were added only for aliases or editors;
    - once the base CLI is 2.3.0, optionally drop the `else` branch of the feature detection (a human-authored workflow edit).

Steps 2 and 3 are independent. Steps 4–5 wait for PILOT-62.

## Mid-flight checkpoint (Tier 2/3)
Step 6.

## Reuse decisions
- Result signing reuses `evidence results sign` and `result_sidecar_ok` unchanged. Only where the files live moves.
- The self-check result reuses `junit_from_tsv.py`, the sensor suite's JUnit writer.
- `--only-results` reuses `_add_results_arg` and `ingest_results`. It only drops the adapter's locations.
- The comment stripper is one helper, shared by the adapter reader and eval front matter.
- Plan references reuse the adapter's existing `artifact_chain.plan_glob` to recognise plan files, with no new adapter key.
- The temp rule keeps `_check_script` and its message. Only which arguments reach it changes, and it reuses `cmdparse.writes_of` and `st.normalize` without editing `cmdparse.py`.
- The git config split keeps `deny_git_config_keys`, `git_allowed_config` and the 2.1.0 `credential.*` rule, and reuses the `ungated` shrink-only merge.
- The `-k` fix reuses `run_hook`. `--suite` reuses the existing suite functions and `sys.argv` parsing.

## Risks
- **Step 5 can lock this session** (hooks read `evidence_policy.py` and `state.py` live). Mitigation: helpers first, small edits, the engine suite after each step. Rollback: `git checkout -- <file>` by the human.
- **An over-broad exemption** would let a planted config key run a program in the key-holding hook. Mitigation: global/system scope only; `ENGINE_ALWAYS_REFUSED` is in code; each always-refused key and the local-scope case have a negative test.
- **A temp data program that can run code** through an option not listed in `_TEMP_EXEC_OPTS`. Mitigation: the set is small and each program was chosen because it does not execute file arguments. A security-reviewer finding adds an option to the list; it does not widen the set.
- **The transitional `sign-and-gate` fallback** runs the 2.1.0 command for one PR. Mitigation: it runs on the downloaded directory, and the owner may choose the follow-up option instead.
- **Test harness change hides a failure:** unselected cases now run their hooks. Mitigation: a full run's pass count is unchanged, which step 9 compares with the count before the change.
- **Rebase conflicts with PILOT-62** (see "Coordination with PILOT-62").
- **Size:** estimate 450–700 changed lines [NEEDS VERIFICATION after step 1].

## Proof

| REQ ID | Requirement | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-USA-01 | `run-tests.sh` writes results to `EVIDENCE_RESULTS_DIR`, outside the working tree by default, clearing stale files | content | yes | — | `tests/content_acceptance_tests.py` "REQ-USA-01 run-tests.sh reads EVIDENCE_RESULTS_DIR and its default is outside the working tree" | CI content.xml |
| REQ-USA-01 | Live: one human run leaves `git status` clean and prints the results directory | manual | no | MAN-USA-01 | — | Pasted terminal output in the PR |
| REQ-USA-02 | The self-check is `run-tests.sh`'s last step; `--self-check` exempts only the hard-coded REQ-V2C-09; an adapter key cannot change it | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-USA-02 …" (only REQ-V2C-09 unproven → exit 0; plus REQ-X-02 → exit 1 naming it; no `--self-check` → exit 1; adapter `self_check_requirement: REQ-X-02` → still blocks) | CI lifecycle.xml |
| REQ-USA-02 | `run-tests.sh` ends with the self-check step and writes `self-check.xml`; the content suite no longer runs `gaps --strict` | content | yes | — | `tests/content_acceptance_tests.py` "REQ-USA-02 run-tests.sh ends with gaps --strict --self-check and the content suite has no in-suite self-check" | CI content.xml |
| REQ-USA-03 | `gaps --only-results` ignores the adapter's result locations; alone it exits 2 | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-USA-03 …" (committed pass ignored → exit 1; without the flag → pass; flag without `--results` → exit 2) | CI lifecycle.xml |
| REQ-USA-04 | CI and the adopter templates sign and read only the freshly downloaded artifact; the GitLab template refuses a tracked results directory | content | yes | — | `tests/content_acceptance_tests.py` "REQ-USA-04 sign-and-gate signs and gates only runner.temp results" and "REQ-USA-04 adopter templates sign only downloaded results; GitLab refuses tracked test-results" | CI content.xml |
| REQ-USA-04 | Live: the first `main` run signs files under `$RUNNER_TEMP` and `sign-and-gate` passes | manual | no | MAN-USA-02 | — | CI run URL in the release note |
| REQ-USA-05 | Inline `#` comments are stripped from adapter values, list items, inline lists and eval `covers:`; quoted or unspaced `#` is kept | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-USA-05 …" (commented glob finds the spec; quoted pattern unquoted; inline list; negative: quoted `#`, `a#b`, commented `covers:` ID not counted) | CI lifecycle.xml |
| REQ-USA-06 | A plan row repeating its `From:` spec's ID is a reference, not a duplicate; genuine duplicates still fail | CLI | yes | — | `plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` "REQ-USA-06 …" (reference → no DUPLICATE-ID; negative: other `From:`, two specs, two plans → DUPLICATE-ID; Tier 1 plan-only ID defined) | CI lifecycle.xml |
| REQ-USA-07 | Temp-directory data commands are judged as paths and allowed | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-USA-07 temp path is data: …" (`mkdir`, `tail`, `ls`, `cat`, `curl -o`, `cp` repo → temp, `sort … > /tmp/b`, `rg`, `mktemp`, `$(mktemp -d)`) | CI engine.xml |
| REQ-USA-08 | Negative: temp-directory execution, code-running options and copies into the repository stay denied | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-USA-08 temp execution still denied: …" (`python3`, `bash`, `source`, `make -f`, `go run`, `awk -f`, `sed -f`, `rg --pre`, `sort --compress-program=`, `curl -K`, `cp /tmp/x src/app.py`, `mv /tmp/x src/other.py`), with the round-4 cases unchanged | CI engine.xml |
| REQ-USA-09 | `-k` selects without changing outcomes; `--suite` runs a subset; no match exits 1; an unknown suite exits 2 | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-USA-09 …" (subprocess: `--suite suite_round4 -k "REQ-V2G-12 round4"` → 1 passed; `-k REQ-IMH` → `0 cases matched`, no traceback; `--suite nope` → exit 2) | CI engine.xml |
| REQ-USA-10 | Engine-ignored keys at global or system scope do not refuse engine git; `credential.*` global as 2.1.0 | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-USA-10 global … is not refused" (scratch `HOME`: `alias.*`, `core.editor`, `core.pager`, `pager.*`, `sequence.editor`, `interactive.diffFilter`, `difftool.x.cmd`; `credential.helper`) | CI engine.xml |
| REQ-USA-11 | Negative: always-refused keys are refused at every scope whatever the policy; ignored keys at local scope are refused; agent `git -c` / `git config` unchanged | engine | yes | — | `plugins/evidence-sdlc/scripts/tests/engine-tests.py` "REQ-USA-11 …" (global `core.fsmonitor`, `core.hooksPath`, `core.sshCommand`, `filter.x.clean`, `diff.x.textconv`, `gpg.program`, `include.path` → refused; local `alias.st`, `core.editor`, `credential.helper` → refused; org `core.*` → `core.fsmonitor` still refused; repo addition dropped; `git config alias.x …` and `git -c core.editor=vim commit` → denied) | CI engine.xml |
| REQ-USA-12 | ADR-0002 rev. 2, docs, governance, CONTRIBUTING, HANDOFF, CHANGELOG 2.3.0 and versions match; both config sets, the temp rule, `--suite` and the owner actions are stated | content | yes | — | `tests/content_acceptance_tests.py` "REQ-USA-12 …" | CI content.xml |

## Considered and rejected
- **Dropping harmless keys from `deny_git_config_keys`,** or exempting them at every scope (see spec, "Rejected alternatives").
- **Skipping hook calls for unselected `-k` cases.** That is the crash.
- **Keeping `self_check_requirement` in `adapter.yml`.** It is agent-editable.
- **Folding re-approval history and `CLAUDE_CONFIG_DIR` into this change.** Both touch `lifecycle.py` / `integrity.py`, which PILOT-62 is changing, and neither is on the CHANGELOG 2.1.0 PILOT-60 list. Proposed as PILOT-64.
- **Fixing the `cmdparse` heredoc merge here.** It belongs to PILOT-59.
