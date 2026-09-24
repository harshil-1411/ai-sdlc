# Changelog

All five plugins are versioned together. Every change to a plugin's files needs a
version bump (enforced in CI by `scripts/ci/check-version-bump.sh`) and an entry here.

## 2.0.0 — 2026-09-24 (PILOT-53, PILOT-51, PILOT-52)

v2 closes every finding of the v1 enterprise audit. Intent, spec and plan:
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
- Semver `version`, homepage, repository, license, keywords and declared
  `dependencies` in every plugin. `claude plugin validate` passes with no warnings.
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
