# Policy reference

The gate engine's policy decides what every rule does: which paths are gated, which
refs are protected, which review agents a tier needs, and so on. The defaults ship in
[`plugins/evidence-sdlc/policy/default-policy.json`](../plugins/evidence-sdlc/policy/default-policy.json).
This page describes every key, the three layers that are merged at load time, and two
worked examples. See [gates-reference.md](gates-reference.md) for the rules the keys
drive.

## The three layers

The policy is loaded fresh on every hook call (`state.load_policy`), in this order:

1. **Default:** `plugins/evidence-sdlc/policy/default-policy.json`.
2. **Organisation:** the file named by `EVIDENCE_ORG_POLICY`. If that isn't set, the
   first of these that exists:
   - macOS: `/Library/Application Support/ClaudeCode/evidence-policy.json`
   - Linux/WSL: `/etc/claude-code/evidence-policy.json`
   - Windows: `C:\Program Files\ClaudeCode\evidence-policy.json`

   The org layer **may change anything**, including loosening a default. Its keys
   replace the default's keys wholesale. A list or map you give (`tier_floors`,
   `required_agents`) replaces the default entirely; it isn't merged. Copy the default
   and edit it. Put the org file next to `managed-settings.json` and deploy it
   the same way, so engineers can't edit it. The engine also treats both directories as
   control plane.
3. **Repository:** `.evidence/policy.json` in the repo. This layer **may only
   tighten** (see [the merge rule](#the-tighten-only-merge-rule-for-repositories)).
   The file itself is control plane, so an agent can't write it and a human edits it.

The session-start context names the layers in force, for example
`policy: default + /etc/claude-code/evidence-policy.json + .evidence/policy.json`.

One environment override exists: `EVIDENCE_ISSUE_KEY_PATTERN`, if set, replaces
`key_pattern` after all three layers are merged.

## The tighten-only merge rule (for repositories)

When `.evidence/policy.json` is merged:

| Key kind | Keys | Merge |
| --- | --- | --- |
| Protection lists | `protected_refs`, `control_plane`, `user_control_plane`, `change_controlled`, `test_globs`, `prod_words`, `read_only_agents`, `non_key_prefixes`, `deny_git_config_keys` | **Union**: the repo can add entries and never remove any |
| Strictness flags | `enforce_claims`, `require_agent_trailer`, `deny_agent_merge`, `require_review_agents`, `deny_tier3_auto_modes`, `deny_opaque_writes`, `scan_secrets`, `treat_unknown_deploy_target_as_production` | **OR**: the repo can turn a flag on, never off |
| `ungated` | | **Can only shrink**: repo entries that aren't already ungated are dropped. The exception is when the org policy sets `allow_repo_ungated_additions: true`; then they are unioned |
| `tier_floors` | | Per glob, the **higher** tier wins, and new globs are added |
| `required_agents` | | Per tier, the agent lists are **unioned** |
| `auto_resolve_max_per_session` (2.2.0) | | **Minimum**: the repo can only lower the cap (a non-integer or negative value is ignored) |
| `tier3_auto_modes_with_required_gate` (2.2.0) | | **Can only become false**: a repo can switch Tier 3 auto modes off, never on |
| Patterns and approval | `key_pattern`, `change_ticket_pattern`, `release_approval_pattern`, `approval` | **Replaced** by the repo value (see the note below) |
| Everything else | e.g. `release_approval_verify_command`, `allow_repo_ungated_additions`, `tier3_denied_permission_modes` | **Ignored** from a repo policy |

> **Note.** The four keys in the "Patterns and approval" row are taken from the repo
> as-is. So a repo policy can widen `change_ticket_pattern` or
> `release_approval_pattern`, or change `approval.mode`. The file is control plane, so
> an agent can't do this. A human with commit rights can, though, so keep
> `.evidence/policy.json` under CODEOWNERS review.

## Every key

### Tracker keys and human-set values

| Key | Default | Meaning |
| --- | --- | --- |
| `key_pattern` | `[A-Z][A-Z0-9]+-[0-9]+` | The tracker-key regex. It is matched in branch names (to find the active change) and commit messages |
| `non_key_prefixes` | `UTF`, `SHA`, `ISO`, `RFC`, `TLS`, `CVE`, `CWE`, `AES`, `RSA`, `WCAG`, `OWASP`, `PCI`, `SOC`, `NIST`, `API`, `REQ` and more | Tokens that match `key_pattern` but aren't tracker keys (`UTF-8`, `SHA-256`, `REQ-12`) |
| `change_ticket_pattern` | `[A-Z][A-Z0-9]+-[0-9]+` | The full-match regex that `CHANGE_TICKET` must satisfy before change-controlled paths can be edited |
| `release_approval_pattern` | `^[A-Z][A-Z0-9]+-[0-9]+$` | The regex that `RELEASE_APPROVAL` must match before a production deploy is allowed |
| `release_approval_verify_command` | `""` (off) | An optional shell command run with `{approval}` substituted. A non-zero exit denies the deploy. Use it to check the release record really exists and is approved in your change system |

### Which paths are gated

| Key | Default | Meaning |
| --- | --- | --- |
| `ungated` | `**/*.md`, `*.markdown`, `*.txt`, `*.rst`, `*.adoc`, `intent/**`, `plan/**`, `.evidence/context/**`, `.evidence/decisions/**`, `LICENSE*`, `NOTICE*`, `CHANGELOG*`, `AUTHORS*`, `.gitignore`, `.evidenceignore` | Paths that need no active change. Everything else in the repo is "source", including JSON, YAML, CI workflows and `package.json` |
| `allow_repo_ungated_additions` | `false` | Org-only. When true, a repo policy can add `ungated` entries |
| `control_plane` | `.claude/settings.json`, `.claude/settings.local.json`, `.claude/hooks/**`, `.claude/agents/**`, `.evidence/policy.json`, `.evidence/secrets-allowlist.json`, `.evidence/changes/*/approval.json`, `.evidence/changes/*/state.json`, `.evidence/audit/**`, `managed-settings.json`, `**/managed-settings.json`, `.mcp.json` | Repo paths no agent may write, by any tool |
| `user_control_plane` | `~/.claude/settings.json`, `~/.claude/settings.local.json`, `~/.claude/plugins/**`, `~/.claude.json`, `/Library/Application Support/ClaudeCode/**`, `/etc/claude-code/**` | Paths outside the repo that no agent may write |
| `change_controlled` | migrations (`**/migrations/**`, `**/migration/**`, `**/db/migrate/**`, alembic, flyway, liquibase, `prisma/schema.prisma`, `**/schema.sql`); CI (`.github/workflows/**`, `.gitlab-ci.yml`, `.circleci/**`, `azure-pipelines.yml`, `Jenkinsfile`, `bitbucket-pipelines.yml`); infra (`**/infra/**`, `**/infrastructure/**`, `**/terraform/**`, `**/*.tf`, `**/*.tfvars`, helm, charts, k8s, kubernetes); `**/audit/**`, `**/signing/**`, `**/crypto/**`, `**/validation/**` | Paths that need `CHANGE_TICKET` in addition to an approved change. Matched case-insensitively |
| `tier_floors` | Tier 3: auth, authn, authz, `auth.*`, `*_auth.*`, `auth_*.*`, `authentication*`, `authorization*`, `oauth*`, `login*`, `session*`, `permissions*`, crypto, signing, audit, migrations, `db/migrate`, `prisma/schema.prisma`. Tier 2: `payment*`, billing, `.github/workflows/**`, `*.tf`, helm, k8s | The minimum tier for a path. An edit in a lower-tier change is denied. Matched case-insensitively; the highest matching floor applies |
| `test_globs` | `test/`, `tests/`, `__tests__/`, `spec/`, `specs/`, `e2e/`, `cypress/`, `playwright/`, `qa/`, `test_*`, `*_test.*`, `*.test.*`, `*.spec.*`, `*_spec.*`, `*Test.java`, `*Tests.java`, `*Test.kt`, `*Tests.cs`, `*.cy.*`, snapshots, `conftest.py`, `pytest.ini`, `tox.ini`, jest/vitest/playwright/cypress/karma/mocha/phpunit configs | What counts as a test file for fix-change test protection |

Globs follow gitignore-style rules. `**/` matches any depth, `*` stays within one path
segment, and a pattern with no `/` matches at any depth. Paths are normalised to
repo-relative form with `realpath` before matching.

### Git, merges and production

| Key | Default | Meaning |
| --- | --- | --- |
| `protected_refs` | `main`, `master`, `trunk`, `develop`, `release`, `release/*`, `releases/*`, `hotfix/*`, `prod`, `prod/*`, `production` | Push targets the agent can never update, from any branch |
| `deny_agent_merge` | `true` | Denies `gh pr merge`, and `gh api` writes to merge, protection, rulesets or refs endpoints. (`gh pr merge --admin` is always denied) |
| `prod_words` | `prod`, `production`, `prd`, `live`, `prod1`, `prod2` | Words that mark a deploy target as production. Matched case-insensitively |
| `treat_unknown_deploy_target_as_production` | `true` | Treats a target computed at run time (`$ENV`) as production |
| `deny_git_config_keys` | `alias.*`, `core.hooksPath`, `core.sshCommand`, `core.fsmonitor`, `core.editor`, `core.pager`, `credential.*`, `include.path`, `includeIf.*`, `filter.*`, `diff.*.textconv`, `sequence.editor`, `gpg.program`, and since 2.1.0 `diff.*.command`, `merge.*.driver`, `core.askPass`, `core.gitProxy`, `core.worktree`, `core.attributesFile`, `gpg.*program`, `ssh.variant`, `remote.*.uploadpack`, `remote.*.receivepack`, `uploadpack.*`, `*tool.*.cmd`, `interactive.diffFilter`, `pager.*`, `url.*.insteadOf`, `submodule.*.update`, `lfs.extension.*`, `lfs.customtransfer.*`, `lfs.standalonetransferagent` | Config keys an agent may not set through `git -c` or `git config`, because each can run arbitrary programs or change authentication. Since 2.1.0 the same list is checked against the config the engine's own git would use: a key in it at any scope except `command` refuses every call (`git-config-refused`), except `credential.*` at global or system scope and exact `git_allowed_config` values. **Known issue:** this also refuses harmless global keys such as `alias.*` and `core.editor`; PILOT-60 splits the list |
| `git_allowed_config` | the four `git lfs install` values: `filter.lfs.clean=git-lfs clean -- %f`, `filter.lfs.smudge=git-lfs smudge -- %f`, `filter.lfs.process=git-lfs filter-process`, `filter.lfs.required=true` | Exact `key=value` pairs that pass the engine's config check although the key is in `deny_git_config_keys`. A value containing a newline or carriage return never passes. Org policy only: a repository policy can't add to it (2.1.0) |

### Changes, reviews and agents

| Key | Default | Meaning |
| --- | --- | --- |
| `enforce_claims` | `true` | Denies source edits outside the approved plan's `## Files claimed` |
| `required_agents` | `{"1": ["verifier"], "2": ["verifier", "security-reviewer"], "3": ["verifier", "security-reviewer", "code-reviewer"]}` | The review agents that must have a recorded completed run before `git push`, `gh pr create` or `evidence change advance KEY verified` |
| `require_review_agents` | `true` | Turns the rule above on |
| `read_only_agents` | codebase-cartographer, security-reviewer, architect, code-reviewer, release-manager, compliance-reviewer, test-designer, stack-surveyor, flake-triage, verifier | Subagent types whose writes are denied. `docs-writer` is deliberately absent |
| `require_agent_trailer` | `true` | Commits must end with `Agent-Session: <session_id>` matching the session |
| `deny_tier3_auto_modes` | `true` | Denies Tier 3 source edits in the permission modes listed below, except as allowed by the server gate (2.2.0, `tier3_auto_modes_with_required_gate`) |
| `tier3_denied_permission_modes` | `bypassPermissions`, `acceptEdits`, `dontAsk`, `auto` | The modes counted as "auto-accept" for Tier 3 |
| `deny_opaque_writes` | `true` | Denies Bash commands that change files in ways the engine can't inspect: inline interpreter code, `patch`, `git apply`/`am`, `curl -O`, archive extraction |
| `scan_secrets` | `true` | Scans write content, command text, heredocs, commit messages and staged diffs for secrets |

### Approval

| Key | Default | Meaning |
| --- | --- | --- |
| `approval.mode` | `"local"` | `local`: approvals come from the prompt (`/evidence-sdlc:approve`) or the terminal, and the approver is `git user.email`. `github`: declares that identity-bound approval through `evidence approve KEY --github-pr N` is the intended path. **Engine 2.0.0 doesn't read this key yet.** Prompt and terminal approvals are still accepted when it is `github`, so don't rely on it to switch local approval off |
| `approval.github_allowed_approvers` | `[]` | The GitHub logins whose APPROVED review, or `/approve-plan <sha12>` comment, counts. The PR author never counts. **If the list is empty, any other GitHub user counts**, so set it |
| `approval.github_repo` | `""` | `owner/repo` for GitHub approvals. Since 2.1.0 it is required: `gh` is always called with `--repo` set to it, and an empty value refuses `evidence approve --github-pr` rather than letting `gh` resolve the repository from agent-writable remotes (REQ-IMH-24). In CI, `verify-range` uses `$GITHUB_REPOSITORY` |

## Example: an organisation policy

Deploy this as `/etc/claude-code/evidence-policy.json` (Linux) or
`/Library/Application Support/ClaudeCode/evidence-policy.json` (macOS):

```json
{
  "key_pattern": "(PAY|CORE|OPS)-[0-9]+",
  "change_ticket_pattern": "CHG[0-9]{7}",
  "release_approval_pattern": "^REL-[0-9]{4,}$",
  "release_approval_verify_command": "/opt/evidence-chain/bin/check-release-record {approval}",
  "approval": {
    "mode": "github",
    "github_allowed_approvers": ["alice-lead", "bob-qa", "carol-security"],
    "github_repo": "acme/payments-api"
  },
  "required_agents": {
    "1": ["verifier"],
    "2": ["verifier", "security-reviewer"],
    "3": ["verifier", "security-reviewer", "code-reviewer", "compliance-reviewer"]
  }
}
```

A human then approves on GitHub, with an APPROVED review or a `/approve-plan <sha12>`
comment, on a PR whose branch carries the key. The agent may run
`evidence approve PAY-142 --github-pr 57` to record it. The CLI checks the login
against the allowlist, rejects the PR author as approver, and checks that the plan blob at the PR head equals the local
plan. Remember that org keys replace defaults, so a `required_agents` given here
replaces the default map.

## Example: a repository policy that tightens

`.evidence/policy.json` (a human commits it; it is control plane):

```json
{
  "protected_refs": ["staging", "env/*"],
  "change_controlled": ["src/ledger/**", "config/feature-flags.yml"],
  "tier_floors": {
    "src/ledger/**": 3,
    "src/reports/**": 2
  },
  "required_agents": {
    "2": ["code-reviewer"]
  },
  "ungated": ["**/*.md"],
  "enforce_claims": false
}
```

The result: `staging` and `env/*` are added to the protected refs, and the ledger and
feature-flag config are added to change control. The ledger gets a Tier 3 floor and
reports a Tier 2 floor. Tier 2 now also needs `code-reviewer`. `ungated` shrinks to
just Markdown. `enforce_claims: false` is **ignored**, because a repo can't turn a
strictness flag off.

## Keys added after the v2 re-audits

| Key | Default | Meaning |
| --- | --- | --- |
| `always_gated` | `CLAUDE.md`, `REVIEW.md`, `AGENTS.md`, `.gitignore`, `.gitattributes` | Markdown and git files that are gated like source even though `*.md` is otherwise ungated: they steer agents, reviewers, or what the integrity monitor can see. |
| `deny_background` | `true` | Deny `cmd &` and subshell backgrounding: work that runs after the command returns escapes both checks. |
| `deny_persistence` | `true` | Deny nohup, setsid, at, crontab, launchctl, systemd-run, screen, tmux, caffeinate. |
| `commit_requires_audit` | `true` | Every commit in an active change must include that change's current audit log, state and approval, and only claimed files. |
| `unsigned_max_tier` | `1` | Highest tier an agent may work on when no `EVIDENCE_SIGNING_KEY` is deployed. Raising it (org policy only) accepts that approvals and records could be forged. |
| `tier3_distinct_approver` | `true` | A Tier 3 plan approved through the prompt or terminal channel must be approved by someone other than the person who started the change. |
| `unknown_programs` | `monitor` | `deny` turns on strict mode: any program not in the built-in known list or `known_programs` is refused, because what it writes cannot be judged. `monitor` leaves them to the integrity monitor. |
| `known_programs` | `[]` | Programs an organisation adds to the strict-mode list. |

## Keys added in 2.1.0 (PILOT-58)

| Key | Default | Meaning |
| --- | --- | --- |
| `git_allowed_config` | the four git-lfs values | See [Git, merges and production](#git-merges-and-production). |
| `verify_range_blob_cap_mb` | `20` | `verify-range` rule 3: a blob added in a PR larger than this fails, unless its path is on `verify_range_allow_large`. Blobs under the cap are scanned for secrets. Read from the base commit's policy plus the org policy, never from the PR. |
| `verify_range_allow_large` | `[]` | Globs of paths allowed to exceed `verify_range_blob_cap_mb` (for example `assets/**/*.png`). Org policy only; a repository policy can't loosen it. |

## Keys added in 2.2.0 (PILOT-62, ADR-0005)

A repository policy may only lower `auto_resolve_max_per_session` and may only set
`tier3_auto_modes_with_required_gate` to false. Every other key below is **ignored** from a
repository policy (org policy only). The engine reads each with an in-code default equal to the
shipped value.

| Key | Default | Meaning |
| --- | --- | --- |
| `auto_resolve_max_per_session` | `3` | How many restored or removed control-plane changes per session are recorded closed at birth (`resolved: "restored"`). Past it, the next one is open and needs a human `clear-violations`. `0` disables closing at birth. |
| `local_settings_kept_keys` | `["model", "outputStyle"]` | Top-level keys of `.claude/settings.local.json` that may change during a call without being restored (display settings). Never list keys that run commands (`hooks`, `statusLine`, `apiKeyHelper`, MCP keys, `env`). |
| `user_config_not_charged` | the managed-settings files, `managed-settings.d/**` and `evidence-policy.json` under `/Library/Application Support/ClaudeCode/` and `/etc/claude-code/` | System config files whose change during a call is logged as `user-config-changed` instead of `hidden-change`, but only when the session's user could not have written them (not owned by the user; neither the file nor its directory writable by the user, before and after the call). |
| `claude_json_security_keys` | `mcpServers`, `allowedTools`, `enabledMcpjsonServers`, `disabledMcpjsonServers`, `enableAllProjectMcpServers` | The per-project keys of `~/.claude.json` that, with the top-level `mcpServers`, form its security projection. Only a change to the projection (or the file becoming invalid, missing or over 64 MiB) is a `hidden-change`. |
| `tier3_auto_modes_with_required_gate` | `true` | Allows Tier 3 source edits in `tier3_gate_allowed_modes` when the session is signed and the server gate is confirmed on GitHub. |
| `tier3_gate_allowed_modes` | `["acceptEdits", "auto"]` | The permission modes the server gate can allow for Tier 3. `bypassPermissions` and `dontAsk` are never allowed, whatever this lists. |
| `ci_gate_check` | `"verify-range"` | The required status check the engine looks for on the default branch. |
| `ci_gate_app_id` | `15368` | The app the check must be pinned to: GitHub Actions. [NEEDS VERIFICATION against a captured `gh api` response.] |
| `ci_gate_require_enforce_admins` | `false` | When true, classic branch protection must also enforce the check for administrators (`enforcement_level: everyone`). |
| `ci_gate_cache_seconds` | `900` | How long a confirmation is cached (signed, in the temp directory). A failure is cached for 60 seconds. |
