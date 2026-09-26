# Changelog

All five plugins are versioned together. Every change to a plugin's files needs a
version bump (enforced in CI by `scripts/ci/check-version-bump.sh`) and an entry here.

## 2.3.0 — 2026-09-26 (PILOT-60)

Usability: the defects that cost a human round trip on every change. Spec, plan and ADRs:
`intent/2026-09-25-usability/`, `.evidence/decisions/0002-ci-owns-test-results.md` (revision 2),
and a dated revision note to `.evidence/decisions/0003-hook-git-is-neutralised.md` §2.

**Owner actions** (details and the exact diff in HANDOFF.md, "PILOT-60 owner actions"):
- apply the `.github/workflows/ci.yml` diff (change-controlled; REQ-USA-04). The content check for it fails until you do;
- run `bash scripts/ci/run-tests.sh` once and confirm a clean `git status` (MAN-USA-01);
- confirm that the first `main` run signs files under `$RUNNER_TEMP` and that `sign-and-gate` passes (MAN-USA-02);
- remove any org `git_allowed_config` entries added only for aliases or editors.

### Test results are CI's signed artifact (ADR-0002)
- `scripts/ci/run-tests.sh` writes to `EVIDENCE_RESULTS_DIR` (REQ-USA-01). The default is outside the working tree, `${TMPDIR:-/tmp}/evidence-chain-results/<repo>-<hash>`, and the script prints it. It clears stale `*.xml`, `*.log` and `*.sig` first, so one run is enough and an agent may run it. `validation/results/` is historical, and nobody commits results.
- The self-check is `run-tests.sh`'s last step (REQ-USA-02): `evidence gaps --strict --self-check --only-results --results "$out"`, written to `self-check.xml` as the proof of REQ-V2C-09. `--self-check` exempts only `REQ-V2C-09`, which is hard-coded in the CLI; no adapter key can change it. The content suite no longer runs `gaps --strict`.
- `evidence gaps --only-results` reads only the `--results` paths (REQ-USA-03). Without `--results`, it exits 2.
- After the `ci.yml` change, `sign-and-gate` downloads the artifact to `${{ runner.temp }}/results` and signs and gates only those files. For the one PR whose base CLI predates `--only-results`, it feature-detects the flag. The adopter GitHub template does the same, and pins v2.3.0. The GitLab template refuses a tracked `test-results/` (REQ-USA-04).

### Traceability CLI
- **YAML comments** (REQ-USA-05). In `.evidence/adapter.yml` values, list items, inline lists and eval `covers:` lines, a `#` that starts the value or follows whitespace, outside quotes, starts a comment. The reader also takes one level of nested mapping, so `artifact_chain.plan_glob` is read; before, it was dropped.
- **Plan references** (REQ-USA-06). Specs are read before plans. When a plan's Proof row repeats an ID that its `From:` spec (or that spec's directory) defines, the row is a reference, not a `DUPLICATE-ID`. Genuine duplicates still fail, and Tier 1 plan-only IDs are still defined.

### Gate engine (evidence-sdlc)
- **Temp-directory paths are judged as paths** (REQ-USA-07, 08). `cat`, `ls`, `tail`, `mkdir`, `grep`/`rg`, `cp`/`mv` *to* a temp directory and the other `_TEMP_DATA_PROGS` no longer trip "Running … from a temporary directory".
  - These stay denied: running code from a temp directory; a temp path given to a code-running option (`rg --pre`, `sort --compress-program`, `curl -K`/`--config`, `wget -e`/`--execute`/`--config`, including `--opt=value`, its abbreviations and `-qKvalue` clusters); a copy into the repository.
  - **Review fixes (M1).** `sort`, `curl`, `wget` and `chmod` are not data programs: a program that needs a code-running-option table can run code. `cp`/`mv` are relaxed only when the temp path is the destination, never a source, and never with `-t` in any form (`-rt`, `-vt`, `--target`). The relaxation never applies when any word is a process substitution (`<(`, `>(`), or when any write of the whole command is inside the repository, opaque or computed (`cat /tmp/x > src/app.py`, `cat /tmp/x | tee -a src/app.py`).
  - **Spec deviation (L1).** The spec's REQ-USA-07 acceptance list names `curl -o $TMPDIR/x.json https://example.com`, `cp src/app.py $TMPDIR/app.bak` and `sort /tmp/a > /tmp/b` as allowed. With the literal `$TMPDIR` the first two are denied ("path computed at run time"): the hook cannot know the shell's `TMPDIR` (the sandbox sets its own), so it does not resolve it. `cp src/app.py /tmp/app.bak` (an expanded path) is allowed. `curl -o` and `sort` are denied with any path, since both are off the data list.
  - `sort --compress-program=/tmp/x`, allowed before, is now denied.
  - Prefixes compare real paths with a trailing `/`.
  - The sandbox-safe form is `mktemp "$TMPDIR/x.XXXXXX"`.
- **Git config split** (REQ-USA-10, 11). The engine's own check no longer refuses `git_config_engine_ignored` keys at **global or system** scope, read from a file the integrity monitor watches (`~/.gitconfig`, `~/.config/git/config`) or a system file the user cannot write (review fix M2; an unwatched `$XDG_CONFIG_HOME/git/config` or a user-owned `/opt/homebrew/etc/gitconfig` is still refused). The new policy key defaults to `alias.*`, `core.editor`, `core.pager`, `pager.*`, `sequence.editor`, `interactive.diffFilter` and `*tool.*.cmd`; a repository policy may only remove entries.
  - `ENGINE_ALWAYS_REFUSED`, in code, keeps every command-running key refused at every scope, whatever the policy says. That includes PILOT-62's `remote.*.url`, `remote.*.pushurl`, `url.*.insteadOf` and `url.*.pushInsteadOf`, and `gpg.*`: `log.showSignature` makes `git log` run `gpg.program`, checked on git 2.46.0.
  - Ignored keys at local or worktree scope are still refused.
  - What an agent may set with `git -c` / `git config` is unchanged.
- `ENGINE_VERSION` 2.3.0.

### Tests
- `engine-tests.py`: `-k` now selects which cases are reported, and unselected cases still run their hooks, so the `suite_round4` crash is gone. `--suite NAME` runs a subset. `0 cases matched` exits 1, and an unknown suite exits 2 (REQ-USA-09). New `suite_pilot60`.
- `cli-lifecycle-tests.py gaps` runs the new `gaps_tests()` (fixtures in `scripts/tests/fixtures/pilot60/`).

### Known issues
- **Proposed as PILOT-64** (key not yet allocated): a plan re-approval missing from `state.json`'s history, and watching `CLAUDE_CONFIG_DIR`.
- A temp path handed to a program that is *not* a data program through `--opt=value` (`make --file=/tmp/x`) is still judged only in its space-separated form (`make -f /tmp/x` is denied), as in 2.2.0.
- `cp -t DIR` into a temp directory is denied: `writes_of` reads the last operand as the destination. It fails closed.
- **For PILOT-59** (`cmdparse.py`, not changed here), found in the PILOT-60 review:
  - process substitution `<(…)`/`>(…)` is not analysed by `cmdparse`: `cat <(bash -c 'echo x > .git/hooks/pre-commit')` is allowed. The temp relaxation adds nothing to it (a command with one is judged as before);
  - the temp rule checks only `argv[1:]`: a temp path as argv[0] (`/tmp/x`) and a relative path after `cd /tmp && …` (`cd /tmp && ./x`) are not judged as temp scripts;
  - environment code injection is not judged: `LD_PRELOAD`, `DYLD_INSERT_LIBRARIES`, `RIPGREP_CONFIG_PATH` set on a command;
  - `writes_of` misparses bundled `cp -t` in general (`cp -rt src other.txt` reads `other.txt` as the destination) (P3);
  - temp content read through stdin (`tee src/app.py < /tmp/x`) or a `file://` URL (`curl -o src/app.py file:///tmp/x`) is judged only by the write's claims, as in 2.2.0.
- **L3.** `run-tests.sh` refuses an `EVIDENCE_RESULTS_DIR` whose real path is inside the working tree (exit 2, before any `rm -f`). The GitLab template's tracked-results guard fails the job when `git ls-files` itself fails (L2).

## 2.2.0 — 2026-09-25 (PILOT-62)

The local layer is advisory in practice. Spec, plan and ADR-0005:
`intent/2026-09-25-local-layer-advisory/`, `.evidence/decisions/0005-local-layer-is-advisory-behind-the-server-gate.md`.
Nothing moves authority from `verify-range` and code-owner review (ADR-0004): rules 0–4 are
unchanged and rule 5 is tightened.

**Owner actions after merge:** in branch protection on `main`, make `verify-range` required
**and set its source to GitHub Actions**; set `approval.github_repo` in the org policy; keep the
org policy root-owned (`sudo`); remove any machine-local permission-mode loosening once a Tier 3
edit in `auto` mode is allowed without it (MAN-LLA-01).

### Integrity monitor (evidence-sdlc)
- **A verified undo is closed at birth** (REQ-LLA-01, 02). A control-plane file the monitor
  restores and re-reads equal to the snapshot, or a created file or planted symlink it removes
  and confirms gone, is recorded `open: false`, `resolved: "restored"`, `resolved_at`, and logged
  with `resolved`. It blocks neither push/PR nor source edits and needs no `clear-violations`.
  Everything else stays open and blocks as in 2.1.0, including a restore whose write fails or
  whose re-read differs.
- **Bounded** (REQ-LLA-03): `auto_resolve_max_per_session` (default 3; 0 disables) per session;
  a repository policy may only lower it.
- **Config edits judged by effect** (REQ-LLA-05, 06, 07): `settings.local.json` allow
  additions/removals, deny/ask additions, `additionalDirectories` changes and
  `local_settings_kept_keys` are kept (`config-change`, or `permission-grant` for a pure allow
  addition), everything else restored; system config in `user_config_not_charged` that the
  session's user could not write is logged as `user-config-changed`; `~/.claude.json` is charged
  only when its MCP/tool-permission projection changes or it becomes invalid, missing or oversize.

### Gates
- **Tier 3 in `acceptEdits` and `auto` follows the server gate** (REQ-LLA-08, 09): allowed when
  `tier3_auto_modes_with_required_gate` is on, the session is signed, and GitHub (read through
  `gh` pinned to `approval.github_repo`) reports `verify-range` required on the default branch and
  pinned to the GitHub Actions app, by classic protection or a ruleset. Cached in a signed temp
  file (900 s confirmed, 60 s not). `bypassPermissions` and `dontAsk` stay denied; the denial names
  the missing condition. `run_gh` now also accepts the endpoint `repos/{repo}` itself.
- **`check-forgery`** (REQ-LLA-10): `gh api` calls that create or update a commit status, check
  run or check suite are denied; reading them is allowed.

### Merge gate
- **`verify-range` rule 5** (REQ-LLA-04) judges entries that first appear in the range: a closed
  entry passes only as a verified restore of an auto-resolvable rule (printed as a `NOTE:` for the
  code owner) or with `cleared_by`.

### Policy
- New keys: `auto_resolve_max_per_session`, `local_settings_kept_keys`,
  `user_config_not_charged`, `claude_json_security_keys`, `tier3_auto_modes_with_required_gate`,
  `tier3_gate_allowed_modes`, `ci_gate_check`, `ci_gate_app_id`, `ci_gate_require_enforce_admins`,
  `ci_gate_cache_seconds`. From a repository policy only the first two merge rules apply (minimum;
  may only become false); the rest are ignored.

### Review fixes (before merge)
- The gate binds to the repository being edited (`origin` must be `approval.github_repo`), and the
  cache is bound to that identity.
- `gh` for gate detection is pinned: `ci_gate_gh_path` (org only) or a root-owned `gh` first on
  PATH; `GH_HOST=github.com` and no other `GH_*`/`GITHUB_*` overrides for every engine `gh` call; a
  gh configuration with `http_unix_socket` or a non-github.com host refuses the gate.
- `settings.local.json`: an `additionalDirectories` addition is restored; a newly created file is
  kept only when it holds only `permissions.allow` entries.
- The auto-resolve cap counts the session across every violations record, so a branch switch does
  not reset it.
- With `ci_gate_require_enforce_admins`, a ruleset-only requirement does not confirm.
- `check-forgery` also covers workflow re-runs, `X-HTTP-Method-Override`, encoded or doubled
  slashes, and GraphQL queries read from a file or `--input`.
- ADR-0005 and SECURITY state what the GitHub Actions pin does not prove (a dispatch from the
  agent's branch or a `pull_request` workflow also produces such a check run); the real control is
  code-owner review plus the `verify-range.yml` hardening proposed in `HANDOFF.md`.

### Re-review fixes
- `origin` for the gate comes from the repository's local config only; a global or system
  `remote.origin.url`/`pushurl`, a differing `pushurl` or any `url.*.insteadOf`/`pushInsteadOf`
  rewrite refuses the gate, and setting those keys (`git config` at any scope, `git -c`) is denied.
  `url.*.pushInsteadOf` joins `deny_git_config_keys`. `remote.*.url` is not added to that list:
  it refuses every call wherever it is set, so it would refuse every repository with a remote.
- The gh configuration check refuses any mention of `http_unix_socket` (quoted, flow style,
  comments), any non-github.com host name in `hosts.yml`, any read error, and a configuration
  directory symlinked outside `$HOME`.
- `check-forgery` and the dispatch rule read gh's words with value-taking flags (`-R`, `-H`, `-F`,
  `-X`, `--jq`, …) and their values removed, so `gh run -R o/r rerun` and `gh workflow -R o/r run
  --ref x` are caught; `-Fquery=@file` is caught.
- Not done: the not-user-writable check on `ci_gate_gh_path` (see HANDOFF).

### Structural fixes (third review)
- Gate detection never reads the user's gh configuration: the token comes from
  `gh auth token --hostname github.com`, and every `gh api` call runs with a root-owned empty
  `GH_CONFIG_DIR`, `GH_TOKEN`, `GH_HOST=github.com` and no other `GH_*`/`GITHUB_*`. This replaces
  the `http_unix_socket` / `hosts.yml` parsing. No token means not confirmed.
- New org-only key `approval.github_repo_roots`: the gate is confirmed only for a listed checkout
  (by real path) whose `origin` matches; unset or empty denies. `origin` is also refused when any
  `include.path`/`includeIf.*` is set, or `remote.pushDefault`/`branch.*.pushRemote` names
  another remote.
- `git config --rename-section`, `--remove-section`, `--edit`/`-e` and the `rename-section`,
  `remove-section` and `edit` subcommands are denied (`git-config-section`); a section rename
  could turn allowed keys into `remote.origin` or `include`. `gh api graphql -F=query=@file` is
  denied.

### Known issues and verification
- **[NEEDS VERIFICATION]** The gate-detection fixtures (`plugins/evidence-sdlc/scripts/tests/fixtures/pilot62/`)
  were **built from GitHub's documented response shapes, not captured**: `gh api` failed in the
  agent sandbox with a TLS error (`x509: OSStatus -26276`). The GitHub Actions app id **15368**,
  the `checks[].app_id` field of "Get a branch" and `integration_id` in "Get rules for a branch"
  must be confirmed against `gh api repos/harshil-1411/ai-sdlc`, `…/branches/main` and
  `…/rules/branches/main`.
- **[NEEDS VERIFICATION]** Whether rules returned by "Get rules for a branch" include
  evaluate-mode rulesets; the engine treats any returned required-status-checks rule as enforced.
- **[NEEDS VERIFICATION]** Claude Code's file layout under `CLAUDE_CONFIG_DIR`: only
  `$CLAUDE_CONFIG_DIR/.claude.json` is handled here; the rest goes to PILOT-60.
- A cache miss may take three `gh` calls (repository, branch, rules), bounded by a 15-second total
  budget inside the hook's 25 seconds; the plan estimated two.
- **Release automation in CI on merge is deferred to PILOT-63.**
- Still open: PILOT-59 (concurrency, signed record changes accepted mid-call), PILOT-60
  (usability), PILOT-61 (key isolation).

## 2.1.0 — 2026-09-25 (PILOT-58)

Integrity-monitor, engine-git and merge-gate hardening. Spec, plan and ADR-0003/0004:
`intent/2026-09-24-integrity-monitor-hardening/`, `.evidence/decisions/`.

**Redeploy note:** the authority moves to CI. Add `.github/workflows/verify-range.yml`, make
`verify-range` a **required status check** on `main`, keep code-owner review required, and
re-run the check after approving a PR (`pull_request_target` doesn't fire on reviews). Pin
`approval.github_repo` if you use GitHub approvals. A required check is matched by name, so keep
`.github/**` under code-owner review. This PR itself is not gated by
`verify-range`: the workflow isn't on `main` until it merges, and it is enforced from the next PR.

### Merge gate (authoritative)
- `evidence verify-range` (REQ-IMH-19), run by the base branch's `pull_request_target` workflow
  (REQ-IMH-21). It reads the PR's commits with git plumbing and fails the PR on ADR-0004 rules 0–5:
  bad inputs; a missing key, trailer or signed state; no code-owner approval of the head commit;
  unclaimed paths; secrets or oversize blobs; audit logs that shrink or go missing; change records
  rolled back, closed without a signed clear, or another change's records edited. On `push` to
  `main`, `--push-report` reports and never blocks.
- Hardened after its code and security reviews (ADR-0004 revision 3):
  - checks run from where the branch left the base (the merge-base), and across the whole range
    as well as per commit, with rename detection off;
  - merges from the base are recognised only when they bring in newer base commits;
  - `.evidence/policy.json` and the secrets allow-list must be claimed;
  - a PR must target the default branch;
  - reviews are read across every page.

### Gates (evidence-sdlc), now advisory for merged history
- Engine git is neutralised (REQ-IMH-09, 22, 24): all git and `gh` calls go through
  `run_git`/`run_gh` with command-running config switched off, attributes from the empty tree,
  and no `GIT_*` or signing key in the child environment. The repository's git config is checked
  once per call: a key in `deny_git_config_keys` at any scope but `command` refuses the call
  (`git-config-refused`), except `credential.*` at global or system scope and exact
  `git_allowed_config` values (the git-lfs defaults). The deny list gains the spec's set and
  `lfs.extension.*`, `lfs.customtransfer.*`, `lfs.standalonetransferagent`. `gh` is always pinned
  with `--repo`; an empty `approval.github_repo` is refused.
- Git failure fails closed (REQ-IMH-23): a repository git can't read denies calls, and after a
  call it is a `git-unavailable` violation, with the control-plane restore still run.
- The integrity monitor never follows a link (REQ-IMH-01, 02, 08): listing, restore and removal
  go through no-follow directory handles, links and non-files at control-plane paths are
  violations, and snapshots are written and read safely with a size cap. It also records
  `.evidence` directory mode and identity changes (REQ-IMH-05), deleted untracked files
  (REQ-IMH-07), rewritten or replaced audit logs by prefix hash (REQ-IMH-20), and its own
  unwritable audit entry, which then denies calls (REQ-IMH-06).
- Commit bypasses denied (REQ-IMH-10): pathspecs, `--only`, `--include`, `--patch`,
  `--interactive`, `--pathspec-from-file`, `git add … && git commit` in one command, and
  `GIT_INDEX_FILE`/`GIT_OBJECT_DIRECTORY`/`GIT_ALTERNATE_OBJECT_DIRECTORIES`.
- `evidence audit verify` reports replayed entries and entries of another session (REQ-IMH-11).
- Audit logs over 64 MiB deny calls instead of hanging the monitor. A pre hook past 25 seconds
  denies; a post hook past 25 seconds records `integrity-timeout`.
- An agent may not dispatch a workflow from another ref (`gh workflow run --ref`, a `/dispatches`
  API call): it would run that branch's own workflow with the repository's secrets and could post
  a check under the merge gate's name.
- A permission granted at Claude Code's prompt ("don't ask again") during a call is kept and
  logged as `permission-grant`, instead of being reverted as tampering. Any other change to
  `.claude/settings.local.json` is still restored.

### Docs and governance
- `gates-reference.md` and `managed-settings.md`: the local push gate is advisory; `verify-range`
  is authoritative; the owner actions. `policy-reference.md`: `git_allowed_config`,
  `verify_range_blob_cap_mb`, `verify_range_allow_large`. `control-mapping.md` and
  `supplier-audit-packet.md` rest change control on `verify-range` and state the ADR-0003 §4
  residual risk.

### Known issues (moved to later changes)
- **PILOT-59:** concurrency (attested writes, signed lease, chained snapshots); a pre-call
  `tool-start` audit entry so a call whose post entry is lost still leaves a trace; FIFO or device
  files in untracked directories can stall the monitor's hashing; the snapshot's root isn't
  compared with the post call's; snapshot files are created world-readable; `cmdparse` merges the
  line after a heredoc into the previous command; the GitHub approval route doesn't compare the
  approver with the change's creator. From the final code review of `verify-range`:
  - a shared log merged with the base's lines first fails rule 4;
  - `.evidence/context/` and `.evidence/decisions/` are ungated locally but must be claimed in CI;
  - non-record files under `.evidence/changes/` and `.evidence/audit/` are exempt from claims;
  - one session's log appended on both sides of a merge fails;
  - whole-range log containment is by set, not by order;
  - `CODEOWNERS` directory patterns without a slash are matched only at the top level;
  - after a post-hook timeout, the alarm is not re-armed;
  - `--o` for `--only` is not caught, though harmless without a pathspec.
- **PILOT-60:** usability: CI-owned test results (ADR-0002), YAML comment handling,
  DUPLICATE-ID for Tier 2+ plans under `plan/`, temp-directory false positives, the
  `engine-tests.py -k` crash, and splitting `deny_git_config_keys` so harmless global keys
  (`alias.*`, `core.editor`, `core.pager`) are not refused.
- **PILOT-61:** isolate the signing key in a signer that never runs git, retiring the ADR-0003 §4
  residual risk.
- **PILOT-62:** make the local layer advisory in practice: a violation the monitor already
  restored doesn't block push, and Tier 3 works in `acceptEdits` once `verify-range` is required.

## 2.0.2 — 2026-09-24 (PILOT-54)

Publication metadata and a security fix to the managed-settings template. Plan: `plan/PILOT-54.md`.

- **Managed-settings template:** absolute paths in `permissions` rules now use `//`
  (`Read(//Library/Application Support/ClaudeCode/**)`, `Read(//etc/claude-code/**)`). With one
  `/`, Claude Code resolves the path relative to the project, so the 2.0.0/2.0.1 rules did not stop
  the Read tool from reading the deployed file and its signing key. That happened on 2026-09-24,
  and the key was rotated. Redeploy the template, or fix the rules in your deployed copy.
  The marketplace `repo` is now `harshil-1411/ai-sdlc`.
- The canary (docs/managed-settings.md) gains a Read-tool step: reading a missing file in the
  managed directory must say "denied", not "file not found".
- `homepage`/`repository` in every plugin, the README install line, and the reference pipeline's
  default repo point at https://github.com/harshil-1411/ai-sdlc. No placeholders remain.
- `.github/CODEOWNERS` added, so the "code-owner review" branch protection actually applies.
- `/evidence-sdlc:start` now says `evidence change start` runs as its own command and is performed
  by the gate engine.
- The supplier audit packet's key-hiding claim now covers the Read tool, and records the defect.

## 2.0.1 — 2026-09-24 (PILOT-57)

The first real session with the signing key deployed could not complete a change. Every earlier
v2 commit had been made from a session running v1 hooks. Spec and plan:
`intent/2026-09-24-signed-lifecycle-fixes/`.

### Gates (evidence-sdlc)
- Human terminal actions (`approve`, `change set-tier`, `change release`, `change clear-violations`)
  failed on a real terminal with "no terminal to confirm on". `/dev/tty` was opened as a read-write
  text stream, which Python refuses on a non-seekable device. It is now opened as separate read and
  write streams.
- Those actions now refuse to write an unsigned record into a repository whose records are signed,
  and say how to supply the key for one command.
- An agent's `evidence change start` / `evidence change advance` is performed by the PreToolUse hook
  with the engine's key, so the change state is signed. Before, the agent's shell (which cannot see
  the key) wrote unsigned state that signed sessions rejected, and refused Tier 2+ as "UNSIGNED MODE".
  Chaining these calls with other programs is refused with a clear message, instead of producing a
  false integrity violation.
- Agent commits on an active change were impossible, because the session audit log gains an entry
  after every call. A staged log may now be behind the file by at most two appended entries. It is
  still denied if altered, truncated or never staged.
- The integrity monitor no longer reports unstaging a file (which moves it into an untracked
  directory) as a write. Untracked directories are now recorded file by file.
- Hardening from this change's security review, since the hook that performs lifecycle calls is not sandboxed:
  - `--intent`, `--spec` and `--plan` must name a `.md` file inside the repository, outside `.git/`,
    `.evidence/`, `.claude/` and the control plane.
  - `--quick` never overwrites a file and never follows a symlinked `plan/` directory out of the repository.
  - The hook acts only in the session's own repository (`CLAUDE_PROJECT_DIR`), not at all in plan mode, and
    never for read-only review agents.
  - The hook performs only `change start <KEY> --tier --kind` and `change advance <KEY> <stage>`. Agents write
    the plan with the Write tool; `--quick/--plan/--spec/--intent` remain for humans. The artifact-path check
    is case-insensitive.
  - A change key must match the tracker pattern and contain only letters, digits, `-` and `_`, for
    every CLI subcommand and in `state.change_dir`, so a key can no longer be a path to another
    repository's state. A state stored under another key's directory is rejected on load.
  - The hook fails closed when `CLAUDE_PROJECT_DIR` is unset, and changes directory to the session
    repository itself (not the agent's path).
  - `advance` refuses to re-sign state whose signature fails. Hook-performed history entries record
    `via: hook` and the agent session.
- Engine writes (state, approvals, violations, audit log, integrity restores) no longer follow a
  symlink or hard link planted in `.evidence/` or anywhere on the path. They run outside the agent's
  sandbox with the key, so a planted link could previously redirect them. This also affected 2.0.0.
- In PostToolUse, an unreadable change state or a write the engine cannot judge is recorded as a
  violation and an `engine-error` audit entry, instead of silently dropping the monitor's findings.
- A commit may leave only this session's own `tool` audit entries unstaged, and only ones that chain,
  hash and verify correctly. A deny or violation entry, even one rewritten in place, must be committed.
- An audit log the engine cannot append to (hard-linked, read-only, replaced by a non-file) is moved
  aside and kept. A fresh log records the replacement and an `audit-tamper` violation is opened. If
  the log cannot be written at all, every call is denied.
- A failure inside the integrity check is recorded as an `integrity-check-error` violation instead
  of silently skipping the check.
- The session audit log no longer forks under concurrent tool calls: appends hold an exclusive lock.
  `evidence audit verify` reports a fork left by older versions as a note, not a failure. It counts
  as a fork only when two different entries of the log's own session were appended from the same
  predecessor, both valid; duplicates and another session's chain spliced in still fail. Deleted, altered or badly signed entries still fail.
- Tests changed to match: two REQ-V2S-01 cases (re-audit golden path; round 4 `--quick`) now expect the
  hook to perform `change start`, instead of the agent's shell.

### Known issues (not fixed here; also present in 2.0.0)
- The integrity monitor's removal of a newly created control-plane file follows symlinked
  directories, so an agent could have files outside the repository deleted (High).
- A directory or other non-file planted at a violations-record path stops violations being
  recorded, and the push gate then reads none (High).
- `git commit -- <paths>` / `--only` bypass the index-based evidence, claims and secret checks.
- `audit verify` checks a fork only against the immediate predecessor. This is reachable only where
  the audit lock is unavailable.
- Integrity snapshots in the shared temp directory are written without symlink checks, and deleting
  a file inside an untracked directory is not judged.
- The control-plane globs cover files under `.evidence/audit/` and similar, but not the directories
  themselves, so a `chmod` of a directory is judged as an ordinary write (the pre-hook still denies
  every call once the audit directory cannot be traversed).
- A plan re-approval is recorded in `approval.json` and the approval audit log, but not in
  `state.json`'s history once the change is implementing.
- The integrity monitor is not safe under concurrent tool calls (parallel subagents). One call's snapshot
  can capture another call's writes and misattribute them, or restore a violation record over a newer
  one. Avoid parallel agents until this is fixed.
- Hooks run `git` outside the sandbox, in the session's repository, with the signing key in their
  environment. Repository-level git configuration that runs commands (`core.fsmonitor`, hooks) is not yet
  neutralised. Not confirmed exploitable; tracked for the next change.

## 2.0.0 — 2026-09-24 (PILOT-53, PILOT-51, PILOT-52)

v2 addresses every finding of the v1 enterprise audit; the v1-vs-v2 audit report lists what was
fixed, what is partial, and what remains an owner action. Intent, spec and plan:
`intent/2026-09-24-v2-enterprise-hardening/`.

### Gates (evidence-sdlc) — breaking
- A single Python gate engine replaces the twelve bash + jq scripts. It fails closed
  on missing python3, malformed input, or any internal error. `jq` is no longer required.
- Source edits need an **active change** for the branch's tracker key, with lifecycle
  state, the artifacts the tier requires, and a plan approved by a human. A plan that
  belongs to another change no longer unlocks edits. Editing the plan voids the approval.
- Bash writes are parsed and judged exactly like Edit/Write. Inline interpreter code
  that writes files is denied.
- Paths are normalised before matching. Directories named `/tmp/` or `/docs/`, `..`
  traversal, `*.json`, `*.yml` and `.claude/*` are no longer exempt.
- Protected-branch pushes are judged by refspec target, from any branch and through
  `git -C/-c`, `env` and absolute-path wrappers. `gh pr merge` and merge/protection
  `gh api` calls are denied.
- The production gate recognises deploy tools by command position, matches target
  environments case-insensitively, and treats computed targets as production. It no
  longer fires on `grep production`.
- Commits need the tracker key in the message (not only the branch name) and an
  `Agent-Session:` trailer. The staged diff is scanned for secrets.
- New: a secret scanner on writes, commands and commits; control-plane protection for
  settings, policy, approvals, change state and audit logs; tier floors by path;
  Tier 3 denied in auto-accept modes; claims enforcement; test protection driven by
  change state (`evidence change advance <KEY> failing-test`); a read-only rule for
  review agents; review agents required before push or PR.
- Declarative policy (`policy/default-policy.json`) with a tighten-only merge of the
  default, org and repo layers.
- A hash-chained audit log in `.evidence/audit/`, including deny verdicts and
  review-agent runs.

- Keyed integrity (`EVIDENCE_SIGNING_KEY`, readable by hooks, hidden from the
  sandbox): approvals, lifecycle state, audit entries, integrity snapshots and CI
  results are HMAC-signed; unsigned or altered records are rejected. Without a key,
  sessions start in a declared UNSIGNED MODE.
- Integrity monitor around every allowed Bash call: control-plane changes restored
  (signed mode) or recorded, unapproved writes recorded and push/PR blocked until a
  human clears them; snapshots bound to their command (replay detected), missing or
  altered snapshots are violations, worktrees supported, timeouts recorded.
- Denied: background execution (`&`, screen, tmux, nohup, at, crontab, launchctl),
  programs read from stdin/pipes/file descriptors/process substitution, nested Claude
  Code sessions, git remote changes, reading the signing key or managed settings.
- Commits must include the change's current evidence and only claimed files; the plan
  must state its tier once and match state; released changes stop unlocking edits;
  reviews count only after the latest source change.

- Unsigned sessions may work only on Tier 1 changes by default; Tier 3 needs a second
  approver; the integrity monitor also watches git hooks/config/excludes, index flags
  that hide edits, ignored entries and the user-level control plane; opt-in strict mode
  refuses unknown programs; CI signs results in a separate job that runs no test code,
  and signatures must be bound to a commit.

### Approval and lifecycle
- Human-only approval through three channels: a human's chat message
  `/evidence-sdlc:approve <KEY> <sha>` (recorded by the UserPromptSubmit hook), the
  terminal (TTY required), or a GitHub review or comment verified against the PR's plan.
- `evidence` CLI shipped in `evidence-sdlc/bin/`, with `change start|status|list|advance|set-tier|release`,
  `approve`, `audit verify` and `metrics`.
- Slash commands: `/evidence-sdlc:start`, `:status`, `:approve`, `:gaps`, `:release-report`.

### Agents and skills
- New agents: architect, code-reviewer, release-manager, docs-writer. New skill:
  release-readiness. New ADR template.
- security-reviewer reports every Critical and High finding. verifier is no longer
  pinned to Haiku. Read-only agents are enforced by the engine.
- secure-api-review covers the OWASP API Top 10 (2023). Organisation specifics come
  from the profile.
- One tier notation (`Risk tier: <n>`). Organisation-specific Part 11 and QA/RA
  wording now reads from compliance.md.
- Every skill description is 500 characters or fewer, with no shared trigger phrases.
  Seven skills with invalid YAML frontmatter were fixed.

### Compliance and governance
- ISO/IEC 27001:2022 and NIST SSDF control sets. Unowned control sets are explicitly
  marked `Owner: UNASSIGNED`.
- `governance/control-mapping.md` maps SOC 2, ISO 27001 and NIST SSDF to mechanisms
  and evidence queries. Governance documents no longer claim enforcement beyond what
  ships.

### Product
- Semver `version`, homepage, repository, license and keywords in every plugin.
  `claude plugin validate` passes with no warnings. Cross-plugin dependencies are
  soft: a hard `dependencies` field was tried and removed after the eval run showed
  it stops a plugin's skills loading when a sibling is absent.
- Repository CI (`.github/workflows/ci.yml`) and runnable reference pipelines
  (`pipelines/`) for GitHub Actions, GitLab, and a CI-hosted agent.
- Managed-settings template: narrow git permissions in place of `Bash(git *)`,
  force-enabled plugins, an OTel env block, and a gates-live canary.
- Personal files removed from the repository. `*.zip` is ignored.

### Testing depth (PILOT-51)
- test-strategy-discovery interview, plus performance, security-testing,
  static-analysis, e2e-ui-testing (Playwright, Selenium and Cypress references) and
  accessibility-testing skills. Test summary report template.

## 1.x
Unversioned. Updates were tracked by git commit SHA; see `git log` before 2026-09-24.
