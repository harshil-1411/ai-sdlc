# Changelog

All five plugins are versioned together. Every change to a plugin's files needs a
version bump (enforced in CI by `scripts/ci/check-version-bump.sh`) and an entry here.

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
