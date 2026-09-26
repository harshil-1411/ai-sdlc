# Handoff — Evidence Chain

For whoever picks this up next (engineer or agent session). Read this first, then
`README.md`. Last updated 2026-09-26 by the maintainer's Claude Code session.

## The decision to know first

**The plugin is feature complete, and gate hardening is frozen.** The AI SDLC plugin
(five plugins, 30 skills, intent → spec → plan → build → review → release, the
traceability CLI) has existed since mid-September. From the v2 hardening on, the work
turned into making the gate engine hold against a *hostile* agent, which means
understanding every possible shell command. That race does not converge: each review
round of PILOT-58, 60, 62 and 59 found new bypasses, and the last one found 21.

So, from 2.4.0:
- **The gates are guardrails against agent mistakes, not a security boundary.** The
  controls to rely on are the `verify-range` merge gate in CI, branch protection,
  code-owner review and the Claude Code sandbox.
- **No new hardening PILOTs** unless a pilot team hits a real problem. Everything still
  open is parked below, with its reason.
- **The next milestone is a pilot, not code:** one real team, one real repo, one week
  (checklist below). The auditors said the same: the remaining score points need owner
  actions and real use, not more engine code.

## Where things stand

| | |
| --- | --- |
| Repository | https://github.com/harshil-1411/ai-sdlc |
| Branches | `main` and `develop` only. All feature branches were merged and deleted on 2026-09-26 |
| Version | 2.4.0, all five plugins and the engine |
| Maintainer | suparn.bector@msbdocs.com; second reviewer Harshil (`harshil-1411`) |
| Enterprise score | **3.3 / 5**, independently verified at `774bba8` on 2026-09-24 (v1 was 2.1). **Not re-scored since**; re-score once, after the pilot |
| Reports | [v1 audit](https://claude.ai/artifact/2AC3mxyFdmkHKYgogwLFpG) · [v1 vs v2](https://claude.ai/artifact/7WPE6snzrdb6DFjjFRBKLC) (private; the owner shares them) |
| Tests | Last full runs: engine 942 passed / 0 failed (PILOT-59 part 1). Content: one known failure, REQ-USA-04, until the owner applies the `ci.yml` diff under "PILOT-60 owner actions" |
| Backup | Every pre-cleanup branch is in `~/Desktop/evidence-chain-backups/evidence-chain-all-branches-20260926.bundle` on the maintainer's machine |

### How 2.2.0 to 2.4.0 reached `main` (needs after-the-fact checks)

PILOT-62 (2.2.0), PILOT-60 (2.3.0), PILOT-59 part 1 (2.4.0) and the PILOT-61 plan were
pushed straight to `main` on 2026-09-26 with branch protection **bypassed**: no pull
request, no code-owner review, no CI run. They were built with the gates switched off,
so the commits carry no `Agent-Session` trailer and `verify-range` rejects the range.
Before the pilot:
1. Run CI on `main` (`gh workflow list`, then `gh workflow run <name> --ref main`) and fix
   anything red.
2. Harshil reviews the range `7759c17..main` after the fact.
3. From now on: feature branch off `develop` → PR into `develop` → PR `develop` → `main`.
   Protect `develop` like `main`.

## PILOT status

| Key | What | Status |
| --- | --- | --- |
| PILOT-51, 52, 53 | v2 hardening | Merged (2.0.x) |
| PILOT-54, 57 | Repo placeholders; human TTY and commit audit | Merged |
| PILOT-58 | Integrity monitor hardening, `verify-range` (2.1.0) | Merged. **Release record never made:** run `evidence change release PILOT-58` (human, with the key) |
| PILOT-62 | Local layer advisory (2.2.0) | Merged |
| PILOT-60 | Usability (2.3.0) | Merged. Owner actions below |
| PILOT-59 part 1 | Review deferrals, REQ-CON-14..23 (2.4.0) | Merged, with 21 known bypasses (CHANGELOG 2.4.0, Known issues) |
| PILOT-59 part 2 | Monitor concurrency, REQ-CON-01..13 | **Parked.** Workaround: run agents one at a time |
| PILOT-59 parser rework | Fail-closed Bash grammar | **Parked.** Two attempts were stopped by the model's safety classifier because the prompts carried working bypass commands |
| PILOT-61 | Signer key isolation | **Parked, plan only** (`intent/2026-09-25-signer-key-isolation/`). Needs admin install on every machine |
| PILOT-63 | Release record written by CI on merge | Parked, proposed (from PILOT-62) |
| PILOT-64 | Plan re-approval missing from history; `CLAUDE_CONFIG_DIR` watching | Parked, proposed |

Reopen a parked item only when a pilot team is hurt by it.

## Next steps, in order

1. **Close out the direct merge** (the three steps above).
2. **Owner actions** (no code can do these):
   - [ ] Apply the `ci.yml` diff under "PILOT-60 owner actions" (it makes REQ-USA-04 pass), then MAN-USA-01 and MAN-USA-02.
   - [ ] Apply the `verify-range.yml` hardening diff under "PILOT-62 owner actions".
   - [ ] Add `verify-range` as a required check on `main`; confirm "Require review from Code Owners" is on; run MAN-IMH-01 on the next PR.
   - [ ] Org policy: `approval.github_identities` (`suparn.bector@msbdocs.com` → `suparnbector`), `approval.mode: "github"`, `approval.github_repo`, `approval.github_allowed_approvers`, `approval.github_repo_roots`, and `ci_gate_gh_path` pointing at a root-owned `gh`.
   - [ ] Confirm the Actions variable `EVIDENCE_REQUIRE_SIGNED=true`.
   - [ ] Capture real `gh api` responses for `repos/…`, `…/branches/main/protection` and `…/rules/branches/main`; the gate fixtures use documented shapes [NEEDS VERIFICATION].
   - [ ] Re-enable the gates on the maintainer's machine (see "Working on this repo").
   - [ ] `evidence change release PILOT-58`.
3. **Pilot** (checklist below).
4. **Re-score once**, after the pilot, with independent auditors and a set budget.

## Pilot checklist

- [ ] Pick one team and one real repository with a tracker (Jira or GitHub Issues) and CI.
- [ ] Install all five plugins; deploy `managed-settings.json` with the signing key; run the canary (`docs/managed-settings.md`); `evidence doctor` is clean.
- [ ] Run discovery; a human answers the `[ASK]` items in `.evidence/context/`.
- [ ] Ship at least one Tier 1, one Tier 2 and one Tier 3 change end to end, each approved by a human in the chat.
- [ ] Merge through `verify-range` and code-owner review; produce `evidence export` for one release.
- [ ] Record, per change: time added by the process, false denials (and the rule), real catches, and anything the team worked around.
- [ ] Exit review after a week: keep, change or drop each gate. Turn real pain into PILOTs; nothing else.

## Working on this repo

- **Gates:** on the maintainer's machine they are **off**. The local, uncommitted
  `.claude/settings.json` disables `evidence-sdlc@evidence-chain`, and the local
  `default-policy.json` is loosened (`develop` and `~/.claude.json` removed from
  protection, `enforce_claims` false, `auto_resolve_max_per_session` 1000,
  `tier3_distinct_approver` false; `.bak` copies beside it). **Never commit these.**
  To turn the gates back on: `git checkout -- .claude/settings.json plugins/evidence-sdlc/policy/default-policy.json`,
  then start a new session and look for `Evidence Chain gates live` in its context.
- **With the gates on:** branch `feature/PILOT-<n>-name` off `develop`, then
  `evidence change start PILOT-<n> --tier <n> --kind feature|fix|chore`, write the
  tier's artifacts, and a human approves with `/evidence-sdlc:approve PILOT-<n> <plan-sha>`.
  Commits need the key and an `Agent-Session: <session id>` trailer. Engine changes are
  Tier 3 and need the signing key or a raised `unsigned_max_tier`.
- **Any plugin file change needs a version bump** in all five `plugin.json` files, the
  marketplace and `ENGINE_VERSION`, plus a CHANGELOG entry (`check-version-bump.sh`).
  The content suite checks they agree.

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

## Parked backlog (reopen only on real need)

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
6. **PILOT-59's 21 bypasses, review H1 and M1:** CHANGELOG 2.4.0, Known issues.

## Decisions worth knowing (and why)

- **One Python engine, not bash + jq.** Pattern-matched bash gates were where the v1 bypasses came from.
- **Signing key held by the hooks, hidden from the sandbox.** The engine and the agent run as the same OS user, so only a secret distinguishes their writes.
- **No `dependencies` in `plugin.json`.** An unmet dependency stops a plugin's skills loading entirely. The eval run caught this: 0 of 43 sdlc cases fired.
- **Versions are back, guarded by `check-version-bump.sh`.** The two earlier reverts happened because a static version made `/plugin update` skip real changes; the check makes a missed bump unmergeable.
- **Background execution is denied.** Work that runs after a command returns escapes both the pre-check and the integrity monitor.
- **Approvals go through UserPromptSubmit.** The model can't author a user prompt. Nested or unattended sessions are refused, and a Tier 3 plan needs a second person.
- **Hardening frozen at 2.4.0 (2026-09-26).** See "The decision to know first".

## Gotchas

- **Hooks load at session start.** Editing `hooks.json` mid-session doesn't change that session's gates, but script *content* is read live.
- **Run agents one at a time.** The monitor is not concurrency-safe (PILOT-59 part 2 is parked).
- **The agent sandbox:** `gh` fails TLS verification (the agent pushes; a human runs `gh pr create`/`merge` and `gh api`); `.git/config` is not writable (`checkout -b`, `push -u` and `branch -D` half-fail: create branches with `git branch X; git symbolic-ref HEAD refs/heads/X; git reset -q`, and set upstreams yourself); `git push` prints `failed to store: 100001` but works (check with `git ls-remote`).
- **Never run `gh auth token`** in an agent session: it prints the real token. The token was rotated on 2026-09-26 after one leaked into a transcript.
- **The literal `$TMPDIR`** in a command stays denied (the hook cannot know the shell's value). Use an expanded path.
- **Absolute paths in permission rules need `//`.** `Read(/Library/…)` is project-relative; `Read(//Library/…)` is the real path. This is how the first signing key leaked (PILOT-54).
- **Human terminal actions need the key for that one command,** run from inside the repo: `EVIDENCE_SIGNING_KEY="$(…)" evidence …` (docs/managed-settings.md). Plan approval goes through the prompt and needs no key.
- **Test results are CI artifacts (ADR-0002).** Nobody commits result files; `validation/results/` is historical.
- **Windows:** native Windows is unsupported; use WSL.
- **Personal files** moved out of the repo are in `~/Desktop/evidence-chain-extras/` on the maintainer's machine.

## PILOT-62 owner actions

Pin `verify-range` to GitHub Actions in branch protection, set `approval.github_repo`
in the org policy, keep the org policy root-owned, and remove the machine-local
permission-mode loosening once MAN-LLA-01 passes.

**`verify-range.yml` hardening (review H4; a human applies it, the agent does not edit
`.github/workflows/`).** A GitHub Actions check run named `verify-range` is not proof by
itself: `gh workflow run verify-range.yml --ref <branch>` runs that branch's workflow
and CLI and attaches the result to the branch head. Proposed diff:

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

Keep `.github/**` under code-owner review: a PR that edits this file, or adds a
`pull_request` workflow with a job named `verify-range`, can still produce a GitHub
Actions check under that name, and only the code owner's review stops it.

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
