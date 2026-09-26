# Handoff — Evidence Chain v2

For whoever picks this up next (engineer or agent session). Read this first, then
`README.md`. Last updated 2026-09-24 by the maintainer's Claude Code session.

## Where things stand

| | |
| --- | --- |
| Repository | https://github.com/harshil-1411/ai-sdlc, branch `main` (only branch on GitHub) |
| Head | `6c32020`: PILOT-53 round 6 |
| Version | 2.0.0, all five plugins |
| Maintainer | suparn.bector@msbdocs.com |
| Enterprise score | **3.3 / 5**, independently verified at `774bba8` (v1 was 2.1). Round 6 (`6c32020`) is not re-scored. |
| Reports | [v1 audit](https://claude.ai/artifact/2AC3mxyFdmkHKYgogwLFpG) · [v1 vs v2](https://claude.ai/artifact/7WPE6snzrdb6DFjjFRBKLC) (private; the owner shares them) |
| Tests | engine 342 · lifecycle 25 · sensor 17 · CLI 80 · content 66, all passing; `evidence gaps --strict` shows 103/103 requirements PROVEN |

The work since the v1 audit is recorded as intent/spec/plan in:
- `intent/2026-09-24-v2-enterprise-hardening/` (PILOT-53)
- `intent/2026-09-24-testing-depth-and-strategy-interview/` (PILOT-51)

`CHANGELOG.md` summarises it.

## What's in the box

- **5 plugins** (`plugins/`): discovery, sdlc, quality, compliance, integrations.
  They contain 30 skills, 11 agents, and 5 slash commands (`/evidence-sdlc:start|status|approve|gaps|release-report`).
- **Gate engine**, `plugins/evidence-sdlc/scripts/engine/`. It's Python stdlib only and fails closed.
  - Entry point: `hook.py`.
  - Rules: `evidence_policy.py`.
  - Shell parsing: `cmdparse.py`.
  - State, policy and audit: `state.py`.
  - Signing: `signing.py`.
  - Post-command monitor: `integrity.py`.
  - CLI lifecycle: `lifecycle.py`.
  - Hook wiring: `plugins/evidence-sdlc/hooks/hooks.json`.
  - Rules are driven by `plugins/evidence-sdlc/policy/default-policy.json`, merged in three layers: default, then org, then repo (tighten-only).
- **`evidence` CLI**, `plugins/evidence-sdlc/bin/evidence`. It's on PATH inside sessions; `cli/evidence` is a shim.
  - Lifecycle: `change start|status|list|advance|set-tier|release|clear-violations`, `approve`, `audit verify`, `metrics`.
  - Traceability: `doctor`, `scan`, `gaps`, `export`, `results sign`, `tracker`.
- **Governance**, `governance/`. `control-mapping.md` maps SOC 2, ISO 27001:2022 and NIST SSDF to mechanisms. Every enforcement claim cites a test.
- **CI**, `.github/workflows/ci.yml`. The `checks` job runs every suite without the key. The `sign-and-gate` job signs results with the *base branch's* CLI and runs `gaps --strict`. Since 2.3.0 (ADR-0002, once the owner applies the `ci.yml` diff under "PILOT-60 owner actions") both use only `${{ runner.temp }}/results`: the fresh artifact is the test evidence, and `validation/results/` is historical. Evals run on manual dispatch only.
- **The merge gate (2.1.0)**, `.github/workflows/verify-range.yml`: a `pull_request_target` job that runs `evidence verify-range` from the base branch against the PR's commits (ADR-0004). It is authoritative; the local hooks are advisory (ADR-0003 §4 states the residual risk). It needs to be a required check on `main`, and must be re-run after approving.
- **Adopter templates**: `managed-settings.json`, `pipelines/` (GitHub Actions, GitLab, CI-hosted agent, CODEOWNERS example), `docs/managed-hooks.example.json`.

## Run and verify

```bash
bash scripts/ci/run-tests.sh                # every suite + the self-check -> JUnit in $EVIDENCE_RESULTS_DIR
                                            # (default outside the repo; the script prints it). One run is enough.
python3 cli/evidence gaps --strict --results <printed dir>   # this repo's own traceability, locally
python3 plugins/evidence-sdlc/scripts/tests/engine-tests.py --suite suite_pilot60 -k REQ-USA  # a fast subset
python3 cli/evidence doctor                 # includes a live gate canary
bash scripts/ci/check-version-bump.sh main  # before merging any plugin change
claude plugin validate . && for p in plugins/*/; do claude plugin validate "$p"; done
```

Evals cost money. Run them per plugin with
`claude plugin eval . --scaffold --allow-tools Write Edit` and regenerate the summary with
`python3 scripts/ci/eval-summary.py <plugin> <results.json>`.

## Working on this repo from now on

This repo is meant to run under its own v2 rules. **It hasn't yet.** v2 was built in a
session still running the v1 hooks, so there's no `.evidence/changes/` or audit trail
for PILOT-53. The plan says so openly. Make the next change the first dogfooded one:

1. Install the plugins from this repo, then start a **new** session. Hooks load at session start.
   ```
   /plugin marketplace add harshil-1411/ai-sdlc
   /plugin install evidence-discovery@evidence-chain   (and the other four)
   ```
2. Create a branch that carries a tracker key, e.g. `feature/PILOT-54-short-name`. The next free key is PILOT-54.
3. Run `evidence change start PILOT-54 --tier <n> --kind feature|fix|chore`, then write the artifacts the tier requires.
4. A human approves by sending `/evidence-sdlc:approve PILOT-54 <plan-sha>` in the chat.
5. Commits need `PILOT-54` in the message, an `Agent-Session: <session id>` trailer, and the change's `.evidence/` files staged.

**Unsigned mode:** without `EVIDENCE_SIGNING_KEY`, agents may only work on **Tier 1**
changes. Engine changes are Tier 3 by the framework's own rules. Before that work you need either:
- the key deployed (`docs/managed-settings.md`, "Signing key"), or
- an org policy that raises `unsigned_max_tier`, which accepts forgeable records.

## Open work

### Code, in priority order
0. **After PILOT-58 (2.1.0):**
   - **PILOT-62, local layer advisory: implemented in 2.2.0 (ADR-0005), not yet merged.** A verified restore is closed at birth (capped per session, shown by `verify-range` rule 5); `settings.local.json`, root-owned system config and `~/.claude.json` edits are judged by effect; Tier 3 in `acceptEdits`/`auto` is allowed when `verify-range` is read from GitHub as required and pinned to GitHub Actions; `check-forgery` denies posting statuses or check runs. **Owner actions after merge:** pin `verify-range` to GitHub Actions in branch protection, set `approval.github_repo` in the org policy, keep the org policy root-owned, and remove the machine-local permission-mode loosening once MAN-LLA-01 passes. The gate-detection fixtures were built from GitHub's documented shapes, not captured [NEEDS VERIFICATION].
   - **Proposed `verify-range.yml` hardening (PILOT-62 review H4, for a human to apply; the agent does not edit `.github/workflows/`).** A GitHub Actions check run named `verify-range` is not proof by itself: `gh workflow run verify-range.yml --ref <branch>` runs that branch's workflow and CLI and attaches the result to the branch head. Proposed diff:
     ```diff
     @@ jobs:
        verify-range:
          runs-on: ubuntu-latest
          timeout-minutes: 15
     +    # a dispatch runs the dispatched ref's copy of this file: only main's copy may judge a PR
     +    if: github.event_name != 'workflow_dispatch' || github.ref == 'refs/heads/main'
          steps:
     +      - name: Refuse a dispatch from any ref but main
     +        if: github.event_name == 'workflow_dispatch'
     +        env:
     +          REF: ${{ github.ref }}
     +        run: test "$REF" = "refs/heads/main" || { echo "verify-range may only be dispatched from main"; exit 1; }
     +
            - name: Check out the base only (the trusted CLI)
              uses: actions/checkout@v4
              with:
     -          ref: ${{ github.event.pull_request.base.sha || github.sha }}
     +          # always the base's evidence CLI: the PR's base for pull_request_target, main otherwise
     +          ref: ${{ github.event.pull_request.base.sha || 'refs/heads/main' }}
                fetch-depth: 0
                persist-credentials: false
     ```
     Keep `.github/**` under code-owner review: a PR that edits this file, or adds a `pull_request` workflow with a job named `verify-range`, can still produce a GitHub Actions check under that name, and only the code owner's review stops it.
   - **`ci_gate_gh_path` is trusted as set** (PILOT-62 re-review item 4, not done): applying the not-user-writable check to it would need a root-owned fake gh in the hook-level tests (ownership, not mode, is what the check tests), so it is left for PILOT-61 (not in PILOT-60's scope). Until then the org must point it at a root-owned gh.
   - **PILOT-63, release automation (deferred from PILOT-62):** `verify-range --push-report` records "merged" in a signed CI artifact that the release command reads. Writing a signed `released` state from CI needs a commit on protected `main` and a human-authored workflow, so it is its own change.
   - **PILOT-59, concurrency and monitor gaps:** attested writes, a signed lease, chained snapshots, a pre-call `tool-start` audit entry (review A4), FIFO/device hashing in `_dirty` (B1), snapshot root mismatch (B2), snapshot directory 0700 plus an owner check (B3), `file_in_commit`-style fail-open sweeps. Also `cmdparse` merges the line after a heredoc into the previous command's argv, and the GitHub approval route doesn't compare the approver with the change's creator.
   - **PILOT-60, usability:** done in 2.3.0 (CHANGELOG). Owner actions are under "PILOT-60 owner actions" below. Review fixes M1, M2, L1-L3 are in; one deviation from the approved spec: its REQ-USA-07 cases with the literal `$TMPDIR` (`curl -o $TMPDIR/x.json`, `cp src/app.py $TMPDIR/app.bak`) and `sort /tmp/a > /tmp/b` stay denied (the hook cannot know the shell's `TMPDIR`; `curl` and `sort` can run code). Use an expanded path. The review's `cmdparse` findings (process substitution, argv[0], environment injection, bundled `cp -t`) are listed for PILOT-59 in CHANGELOG 2.3.0.
   - **PILOT-64 (proposed, key not yet allocated):** a plan re-approval missing from `state.json`'s history, and watching `CLAUDE_CONFIG_DIR`. Both touch `lifecycle.py` / `integrity.py`.
   - **PILOT-61, key isolation:** a signer that never runs git or exposes the key, which retires ADR-0003 §4.
1. **Inline interpreter code** (`python -c`, `node -e`) is judged by a keyword denylist
   (`cmdparse._WRITE_HINTS`), so string tricks get past the pre-check. Replace it with an
   allowlist of read-only forms, or make strict mode the default.
2. **Gitignored content** isn't watched by the integrity monitor: writes inside ignored
   directories, and edits to existing ignored files. Hash a configured set such as `.env*`
   and build configs.
3. **About half of `tests/content_acceptance_tests.py` is keyword-presence.** Replace these
   with structural checks: sections filled, REQ IDs resolve, and referenced tests exist and ran.
4. **Review content** isn't checked, only that the required agent completed after the latest change.
5. **Stale `REQ-GATE-*` rows** in `validation/traceability.csv` are kept deliberately:
   they're evidence of a 2026-09-12 run, and rows are never rewritten. `export --conflicts-only`
   flags them. Supersede them with new rows rather than editing them.

### Owner actions (no code can do these)
- [x] Replace the organisation placeholders with `harshil-1411/ai-sdlc` (2026-09-24, PILOT-54; the maintainer edited `managed-settings.json`).
- [x] Branch protection on `main`: `checks` and `sign-and-gate` required, code-owner review, no force pushes (2026-09-24).
- [x] `.github/CODEOWNERS` with a real handle (2026-09-24, PILOT-54).
- [x] `EVIDENCE_SIGNING_KEY` Actions secret: `sign-and-gate` passed on PR #1 (2026-09-24).
- [ ] Confirm the Actions variable `EVIDENCE_REQUIRE_SIGNED=true` is set (not verified).
- [ ] After PILOT-58 merges: add `verify-range` as a required status check on `main`, and confirm "Require review from Code Owners" is on. Then run MAN-IMH-01 on the next PR: a deliberately bad branch must fail `verify-range`, and pass after a code-owner approval and a re-run.
- [ ] A second person for code-owner review. The owner in CODEOWNERS can't approve their own PRs, so until a second reviewer exists, merges need the admin override.
- [ ] Set up GitHub approval mode in an org policy:
  - `approval.mode: "github"`
  - `github_repo`
  - `github_allowed_approvers`
- [x] Deploy `managed-settings.json` with the signing key and sandbox, on the maintainer's machine (2026-09-24). The first key was read through the Read tool because of the single-`/` defect, and has been rotated. The env probe and the Read of the managed directory are now both denied. Run the canary (docs/managed-settings.md) on every other machine.
- [ ] Run the evals that weren't run for budget:
  - compliance
  - the rest of sdlc and discovery, at 3 or more runs per arm
  - the live scenarios
- [ ] Pilot with one team for 60–90 days, commission an external red team, then re-score.

## Decisions worth knowing (and why)

- **One Python engine, not bash + jq.** Pattern-matched bash gates were where the v1 bypasses came from.
- **Signing key held by the hooks, hidden from the sandbox.** The engine and the agent run as the same OS user, so only a secret distinguishes their writes.
- **No `dependencies` in `plugin.json`.** An unmet dependency stops a plugin's skills loading entirely. The eval run caught this: 0 of 43 sdlc cases fired.
- **Versions are back, guarded by `check-version-bump.sh`.** The two earlier reverts happened because a static version made `/plugin update` skip real changes; the check makes a missed bump unmergeable.
- **Background execution is denied.** Work that runs after a command returns escapes both the pre-check and the integrity monitor.
- **Approvals go through UserPromptSubmit.** The model can't author a user prompt. Nested or unattended sessions are refused, and a Tier 3 plan needs a second person.

## Gotchas

- **Hooks load at session start.** Editing `hooks.json` mid-session doesn't change that session's gates, but script *content* is read live.
- **GitHub history:** `main` on GitHub was force-replaced once on 2026-09-24. It had only GitHub's "Initial commit" README.
- **Local branches:** `master` is the old v1 line, and `hardening/v2` has the same head as `main`. Both are local only.
- **Windows:** native Windows is unsupported; use WSL.
- **Absolute paths in permission rules need `//`.** `Read(/Library/…)` is project-relative; `Read(//Library/…)` is the real path. This is how the first signing key leaked (PILOT-54).
- **Run review agents one at a time.** Parallel subagents made the integrity monitor attribute one agent's writes to another, restore over a real violation record, and fork the audit log (PILOT-57). Monitor concurrency is PILOT-58.
- **Human terminal actions need the key for that one command:** `EVIDENCE_SIGNING_KEY="$(…)" evidence …` (docs/managed-settings.md). Plan approval goes through the prompt and needs no key.
- **Test results are CI artifacts (2.3.0, ADR-0002).** Nobody commits result files. `bash scripts/ci/run-tests.sh` writes to `EVIDENCE_RESULTS_DIR` (default outside the repo, printed), ends with the self-check that proves REQ-V2C-09, and leaves `git status` clean, so an agent may run it too. One run is enough. `validation/results/` is historical.
- **The agent sandbox can't open PRs:** `gh` fails TLS verification there. The agent pushes, and a human runs `gh pr create`/`merge`.
- **Personal files** moved out of the repo are in `~/Desktop/evidence-chain-extras/` on the maintainer's machine.

## PILOT-60 owner actions

1. **Apply the `.github/workflows/ci.yml` change below** (change-controlled, human-authored; REQ-USA-04) and commit it on the PILOT-60 branch before merging. The content check "REQ-USA-04 sign-and-gate signs and gates only runner.temp results" fails until it is applied. Save the block to a file and run `git apply <file>`. The `else` branch runs the 2.1.0 command on the downloaded directory for the one PR whose base CLI predates `--only-results`. Once the base CLI is 2.3.0, a human can drop it.
2. **MAN-USA-01:** run `bash scripts/ci/run-tests.sh` once in your terminal, and confirm that it prints the results directory and `self-check: passed`, and that `git status --short` shows nothing new.
3. **MAN-USA-02:** confirm that the first `main` CI run after the merge signs files under `$RUNNER_TEMP` and that `sign-and-gate` passes.
4. Remove any org `git_allowed_config` entries that were added only so a global alias or editor would pass.

```diff
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -41,13 +41,16 @@
       - name: Python compiles
         run: python3 -m py_compile plugins/evidence-sdlc/scripts/engine/*.py plugins/evidence-quality/scripts/*.py plugins/evidence-sdlc/scripts/cli/*.py
 
-      - name: All suites (engine, lifecycle, sensor, CLI, content) -> fresh JUnit in validation/results
+      - name: All suites (engine, lifecycle, sensor, CLI, content) and the self-check -> fresh JUnit in runner.temp/results
+        env:
+          EVIDENCE_RESULTS_DIR: ${{ runner.temp }}/results
         run: bash scripts/ci/run-tests.sh
 
       - uses: actions/upload-artifact@v4
+        if: always()
         with:
           name: validation-results
-          path: validation/results/
+          path: ${{ runner.temp }}/results/
 
       - name: Version bump check
         if: github.event_name == 'pull_request'
@@ -82,7 +85,7 @@
       - uses: actions/download-artifact@v4
         with:
           name: validation-results
-          path: validation/results/
+          path: ${{ runner.temp }}/results/
       - name: Trusted signer = the base branch's CLI, never the PR's own copy
         run: |
           base="${{ github.base_ref || github.event.repository.default_branch }}"
@@ -98,11 +101,16 @@
         env:
           EVIDENCE_SIGNING_KEY: ${{ secrets.EVIDENCE_SIGNING_KEY }}
         run: |
-          if [ -n "$EVIDENCE_SIGNING_KEY" ]; then python3 ../trusted/plugins/evidence-sdlc/bin/evidence results sign validation/results/*.xml; fi
-      - name: Traceability gaps (strict, trusted CLI)
+          if [ -n "$EVIDENCE_SIGNING_KEY" ]; then python3 ../trusted/plugins/evidence-sdlc/bin/evidence results sign "$RUNNER_TEMP"/results/*.xml; fi
+      - name: Traceability gaps (strict, trusted CLI, only this run's downloaded results)
         env:
           EVIDENCE_SIGNING_KEY: ${{ secrets.EVIDENCE_SIGNING_KEY }}
-        run: python3 ../trusted/plugins/evidence-sdlc/bin/evidence gaps --strict
+        run: |
+          if python3 ../trusted/plugins/evidence-sdlc/bin/evidence gaps --help | grep -q -- --only-results; then
+            python3 ../trusted/plugins/evidence-sdlc/bin/evidence gaps --strict --only-results --results "$RUNNER_TEMP/results"
+          else
+            python3 ../trusted/plugins/evidence-sdlc/bin/evidence gaps --strict --results "$RUNNER_TEMP/results"
+          fi
 
   evals:
     if: github.event_name == 'workflow_dispatch' && inputs.run_evals
```
