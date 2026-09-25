# Intent: Remove the usability defects that cost a human round trip on every change

Tracker: PILOT-60   Author: Suparn Bector (maintainer), drafted by Claude from the CHANGELOG 2.1.0 "Known issues" and the PILOT-58 dogfooding findings   Date: 2026-09-25   Status: draft

## Problem
CHANGELOG 2.1.0 moved six usability defects to PILOT-60. Each was reproduced on `7759c17` (origin/main) on 2026-09-25, except where marked:

- **Committed test results (ADR-0002, Proposed, deferred to this change).**
  - `scripts/ci/run-tests.sh` writes JUnit into `validation/results/`, which is committed and change-controlled (`**/validation/**`), so an agent cannot run the whole suite.
  - The content suite's REQ-V2C-09 check (`tests/content_acceptance_tests.py:298–307`) runs `evidence gaps --strict` *before* the suite writes its own `content.xml`. The maintainer runs `run-tests.sh` twice and commits the results on every change (`HANDOFF.md:140`).
  - The ADR-0002 design review found two defects in its own draft: `self_check_requirement` in the agent-editable `adapter.yml` could exempt any requirement, and CI's `sign-and-gate` signs whatever sits in `validation/results/` (`.github/workflows/ci.yml:82–105`), including files committed by the PR. The adopter template `pipelines/github-actions/evidence-chain.yml:68–84` has the same shape (`test-results/`).
- **YAML comments.** `evidence_trace.load_adapter` (`plugins/evidence-sdlc/scripts/cli/evidence_trace.py:132`) skips whole-line comments only. An inline `# comment` stays in the value. Reproduced: `- intent/*/spec.md   # specs` becomes the glob `intent/*/spec.md   # specs`; `tracker_pattern: "[A-Z]+-[0-9]+"  # keys` keeps its quotes and the comment; `[validation/results]  # junit` is read as a string, not a list. This silently broke a glob in PILOT-54. `find_eval_covers` (`:411`) also reads IDs inside a comment on a `covers:` line.
- **DUPLICATE-ID for Tier 2+ plans under `plan/`.** `.evidence/adapter.yml` lists `plan/*.md` in `spec_glob` so Tier 1 plans define requirements (REQ-P54-07). `build_graph` (`:994`) counts every table row whose cell is an ID as a definition. A Tier 2+ plan saved as `plan/<KEY>.md` repeats its spec's IDs in its Proof table. Reproduced in a scratch repository: `REQ-X-01: defined in intent/2026-01-01-x/spec.md, plan/ABC-1.md`, and `gaps --strict` blocks.
- **Temp-directory false positives.** `evidence_policy.check_bash` (`:871–876`) passes *every* argument that starts with a temp directory to `_check_script` (`:776`), which denies it as "Running … from a temporary directory". Reproduced through the hook: `mkdir -p $TMPDIR/probe`, `tail -5 /tmp/build.log`, `ls $TMPDIR`, `cat /private/tmp/x.txt`, `curl -o $TMPDIR/x.json …`, `cp src/app.py $TMPDIR/app.bak` and `sort /tmp/a > /tmp/b` are all denied `opaque-write`. `mktemp` is **not** refused by the gate (allowed through the hook). It fails in the Claude Code sandbox on macOS because it ignores `TMPDIR` and uses `/var/folders/…` ("mkstemp failed … Operation not permitted"); `mktemp "$TMPDIR/x.XXXXXX"` works.
- **`engine-tests.py -k` crashes in `suite_round4`.** Reproduced: `-k REQ-IMH` (or any filter that skips the round-4 cases) raises `FileNotFoundError: … .evidence/audit/s1.jsonl` at `engine-tests.py:860`, because a filtered-out `case()` never runs its hook, so the audit log the next step appends to is never created. `-k REQ-V2G-12` does not crash but reports a false failure for the same reason (state that earlier skipped cases would have produced is missing).
- **`deny_git_config_keys` refuses harmless global keys.** Since 2.1.0 `state.check_git_config` (`state.py:114`) refuses every engine git call when any key in the list is set at any scope except `command`. Reproduced: a user `~/.gitconfig` with `alias.st = status` refuses with "git config alias.st (global, …) can make git run a command". Every developer with a git alias or a configured editor is locked out until a human edits their global config or the org allow-lists the exact value.

## Proposed outcome
1. Test results are produced by CI and signed there. Nobody commits result files, an agent can run `run-tests.sh`, and one local run is enough.
2. The adapter reader and eval front matter treat `#` comments as YAML does.
3. A Tier 2+ plan that repeats its own spec's IDs is not a duplicate.
4. Commands that only read, list, create or download a temp-directory path are judged like any other path; running code from a temp directory stays denied.
5. `engine-tests.py -k` selects cases without changing their outcome, and a new `--suite` option makes a subset fast.
6. The engine's own config check ignores global keys that git only uses interactively (aliases, editors, pagers), while every key that makes git run a command in the engine's calls stays refused, and what an agent may set is unchanged.

**Measure:**
- the next change after this one ships needs no committed file under `validation/results/` and no second `run-tests.sh` run;
- each reproduction above passes (or is judged by its real target), each with a test;
- each command-running config key, temp-directory execution form and genuine duplicate still fails, each with a negative test.

## Affected users and systems
- The gate engine (`evidence_policy.check_bash`, `state.check_git_config`, policy merge) and the traceability CLI (`evidence_trace.py`: adapter reader, requirement graph, `gaps`).
- `scripts/ci/run-tests.sh`, `.github/workflows/ci.yml` and the adopter CI templates under `pipelines/`.
- Every repository that runs the plugins, including msb_clm. Every developer with a git alias or editor in their global config.
- Maintainers, who carry the result commits and the second test run today.

## Regulated record impact
Yes, indirectly. Test results are compliance evidence: where they are produced, signed and read changes. They stay signed by CI with the base branch's CLI. No violation, approval or audit record format changes.

## Compliance evidence impact
Yes. `validation/results/` becomes historical (ADR-0002). `governance/control-mapping.md` and `governance/supplier-audit-packet.md` point to signed CI artifacts as the test evidence. No regulatory framework is established for this repository (`.evidence/context/compliance.md`: all `[ASK]`).

## Data classification
None. The signing key is a secret that must never be read or exposed, and no change may read it. The git config split must not widen what the key-holding hook process can be made to execute (ADR-0003).

## Constraints
- **No weakening of what merges.** `sign-and-gate` still signs with the base branch's CLI and runs `gaps --strict`; after this change it signs only the freshly downloaded artifact. `verify-range` (ADR-0004) is untouched.
- **Every loosening has a negative test:** each always-refused config key, each temp-directory execution form, a genuine duplicate ID, a commented value that must be kept.
- **What an agent may set in git config is unchanged:** `git -c` and `git config` still deny every key in `deny_git_config_keys`.
- **Tier 3 process:** plan approval by a second human (Harshil); review agents run one at a time; no edits during a review.
- **Human-authored files:** `.github/workflows/ci.yml` is change-controlled. The agent writes the exact diff in the plan; the human applies it.
- **Backwards compatible:** existing adapters, specs, plans, policies and committed results still parse and verify.
- **Sequenced after PILOT-62**, which touches the same engine files, tests, docs and versions (plan, "Coordination with PILOT-62").

## Out of scope
- The `cmdparse` heredoc bug (the line after a heredoc merges into the previous command) and every other PILOT-59 item. This change does not edit `cmdparse.py`.
- Key isolation (PILOT-61); anything PILOT-62 claims beyond the shared files.
- A plan re-approval missing from `state.json`'s history (listed under PILOT-60 in the PILOT-58 intent, but not in CHANGELOG 2.1.0) and `CLAUDE_CONFIG_DIR` watching (handed to PILOT-60 by the PILOT-62 spec). Both are proposed as separate changes (spec, "Out of scope").
- The Claude Code sandbox's `mktemp` behaviour, which is not an engine defect. Docs give the working form.

## Open questions
- Should the global-only exemption also cover `credential.*`? It already passes at global and system scope in 2.1.0 and is kept as is. Owner: maintainer.
- Is a feature-detected `ci.yml` step (new flags when the trusted CLI has them) acceptable for the one PR where the base CLI predates them, or should the `ci.yml` edit follow as a separate human commit after merge? Owner: maintainer (spec, "Areas of concern").
