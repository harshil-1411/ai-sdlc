# Gates reference (engine v2)

Every gate decision in Evidence Chain is made by **one engine**:
`plugins/evidence-sdlc/scripts/engine/`. The engine is Python 3.8+ and uses only the
standard library. This page covers:

- the engine's parts and how it is wired into Claude Code;
- how it fails closed;
- every rule, with its requirement ID, what it denies, the deny message, the
  legitimate way past it, and where it is tested;
- the advisory hooks.

What each rule matches is set by policy. See [policy-reference.md](policy-reference.md).

The requirement IDs (`REQ-V2G-…`, `V2S`, `V2A`, `V2K`, `V2X`) come from
[`intent/2026-09-24-v2-enterprise-hardening/spec.md`](../intent/2026-09-24-v2-enterprise-hardening/spec.md).
`REQ-IMH-…` come from [`intent/2026-09-24-integrity-monitor-hardening/spec.md`](../intent/2026-09-24-integrity-monitor-hardening/spec.md) (2.1.0).

## Where the authority is (2.1.0, ADR-0004)

**The local hooks are advisory.** They run on the developer's machine, in a repository the agent
can shape, so a determined agent can get past them (ADR-0003 §4 states the residual risk). They
give early feedback and keep the audit record. They are not what decides a merge.

**The authoritative gate is `verify-range`**, a `pull_request_target` job in
`.github/workflows/verify-range.yml`. `pull_request_target` runs the **base branch's** copy of the
workflow, so a PR cannot edit or remove the gate that judges it. The job checks out only the base
(the trusted CLI), fetches the PR's objects, and runs `evidence verify-range`, which reads them
with git plumbing and executes nothing from the PR. It fails the PR when (ADR-0004 rules 0–5):

| Rule | Fails when |
| --- | --- |
| 0 | the event, SHAs, signing key (32+ characters) or token are missing or malformed, the fetched PR head is not the event's head, or the PR doesn't target the default branch |
| 1 | the head branch doesn't carry exactly one change key; a commit lacks the key or an `Agent-Session:` / `Human-Commit:` trailer; the change state is unsigned or released; `approval.json` doesn't match the plan's hash; or no **code owner** of every changed path (the base's `CODEOWNERS`, last matching rule) approved the **head commit**, other than the PR author |
| 2 | any path, in any commit, any merge or the net diff, is outside the plan's claims. Only `.evidence/audit/`, `.evidence/changes/` and `.evidence/violations/` are exempt, because rules 4–5 judge them; `.evidence/policy.json` and the secrets allow-list must be claimed |
| 3 | an added blob holds a possible secret, or is over `verify_range_blob_cap_mb` and not on `verify_range_allow_large` |
| 4 | a named session's audit log is missing or doesn't verify, a base log is deleted, or any log is not an append-only extension of its parent's |
| 5 | a change record is unsigned, deleted or rolled back, a violation is closed without a signed clear, an entry first appears closed without a signed clear or a verified restore (2.2.0), or another change's record is edited other than by a signed release or clear. An entry closed at birth by a verified restore passes and is printed as a `NOTE:` line for the code owner |

On `push` to `main`, `verify-range --push-report` checks rules 2–5 after the fact and reports
without blocking (it catches admin direct pushes). The existing `sign-and-gate` job (results
signing and `gaps --strict`) is unchanged.

**Owner actions:**
- Make `verify-range` a **required status check** on `main`, and keep "Require review from Code
  Owners" on. Without the required check, nothing is enforced. Since 2.2.0, **set the check's
  source to GitHub Actions** (branch protection, or `integration_id` in a ruleset): Tier 3 auto
  modes are allowed only when the engine reads that pin from GitHub (see below).
- `pull_request_target` does not fire on reviews. **After approving, re-run** the PR's
  `verify-range` job ("Re-run jobs" on its check). That run is the one attached to the PR's head
  commit. A `workflow_dispatch` run with the PR number re-checks the PR too, but its result is
  attached to the dispatching branch's commit, so it doesn't satisfy the PR's required check.
- **Fork PRs** (and Dependabot) fail by design: they get no secrets, so there is no key to verify
  records with.
- **A required check is matched by name.** A workflow on a PR branch with a job named
  `verify-range` could post a passing check under that name. What stops it is code-owner review
  of `.github/**`: CODEOWNERS covers it, so such a PR needs a code owner to approve the new
  workflow. Where the host supports it, pin the requirement to this workflow file on `main`
  (a ruleset's "require workflows"). The engine also denies an agent dispatching a workflow from
  another ref (`gh workflow run --ref`, a `/dispatches` API call), which would run that branch's
  own workflow with the repository's secrets.
- A commit with a `Human-Commit:` trailer needs no audit log (there is no agent session behind
  it). It is covered by the code-owner review of the head commit like every other commit.

## The engine

| File | Role |
| --- | --- |
| `hook.sh` | Launcher. If `python3` (or `$EVIDENCE_PYTHON`) is missing, it denies every PreToolUse and says so at SessionStart |
| `hook.py` | Entry point for the events `pre`, `post`, `prompt`, `session-start` and `sensor`. Reads the hook JSON, writes the response and the audit entries |
| `evidence_policy.py` | Every PreToolUse rule (`decide_pre`) |
| `cmdparse.py` | `shlex`-based Bash analysis. Splits on `;`, `&&`, `\|\|`, `\|` and newlines. Strips wrappers (env assignments, `env`, `command`, `sudo`, `nice`, `time`). Recurses into `bash -c`, `$(…)`, backticks and `eval`. Finds write targets, push refspecs, commit messages and deploy invocations |
| `secretscan.py` | The secret patterns, entropy checks and fingerprints |
| `state.py` | Policy loading and merging, change state, approvals, plan parsing (claims), and the hash-chained audit log |
| `lifecycle.py` | The `evidence change / approve / audit / metrics` commands, and prompt approval |
| `sensor.py` | Advisory template checks (PostToolUse) |

**Wiring** (`plugins/evidence-sdlc/hooks/hooks.json`):

| Event | Matcher | Calls |
| --- | --- | --- |
| PreToolUse | `Edit\|Write\|MultiEdit\|NotebookEdit\|Bash\|Agent\|Task` | `hook.sh pre`, which applies the rules below |
| PostToolUse | same | `hook.sh post`, which writes audit entries, records review-agent runs, moves the change to `implementing`, and runs the sensor |
| UserPromptSubmit | (all) | `hook.sh prompt`, which records a human's `/evidence-sdlc:approve KEY SHA` |
| SessionStart | (all) | `preflight.sh`, then `hook.sh session-start`, which prints the canary line `Evidence Chain gates live (engine …; policy: …)` and the active change's status |

No `if` filters are used. Every Bash call reaches the engine (REQ-V2G-11).

**Legacy scripts.** Engine v2 replaces the twelve bash + `jq` scripts that v1 used
(`gate-plan-exists.sh`, `protect-validated-paths.sh`, `block-test-weakening.sh`,
`block-protected-branch-push.sh`, `production-gate.sh`, `audit-log.sh`,
`session-context.sh`, `template-sensor.sh`, evidence-quality's `require-issue-key.sh`,
and others). No `hooks.json` references them any more, and v2 removed them. If you
wired one of those paths into your own settings, point it at
`scripts/engine/hook.sh <event>` instead (see `docs/managed-hooks.example.json`).

## Failing closed (REQ-V2G-01)

| Condition | Result |
| --- | --- |
| `python3` not on `PATH` | Every PreToolUse is denied: *"The Evidence Chain gate engine needs python3 on PATH and cannot find it, so no gate can run. Failing closed."* SessionStart says `EVIDENCE CHAIN GATES NOT RUNNING` |
| Empty, non-JSON or non-object hook input | `malformed`: *"Gate engine could not read the hook input (…); failing closed."* |
| An Edit or Write with no path, or a Bash call with no command string | `malformed`: *"… refusing rather than guessing."* |
| A command that can't be parsed (unbalanced quotes, nesting too deep) | `unparseable`: *"This command could not be parsed reliably … Rewrite it more simply."* |
| Any exception inside the engine | `engine-error`: *"Gate engine error (…); failing closed. Report this with the command that triggered it."* |

PostToolUse, UserPromptSubmit and SessionStart never block. Audit-log failures are
printed to stderr and never break a session.

One limit sits outside the engine. Claude Code treats a hook that **cannot be
executed at all** (a bad path, or `bash` itself missing) as *allow*. The canary line is
how you detect that. See [managed-settings.md](managed-settings.md#the-canary).

## Human-only overrides

There is no agent-reachable bypass. The only ways past a rule are human ones:

| Override | Who sets it | Unlocks |
| --- | --- | --- |
| `CHANGE_TICKET` | The human who launches the session (shell env or managed/user settings). It must fully match `change_ticket_pattern` | Change-controlled paths |
| `RELEASE_APPROVAL` | The same. It must match `release_approval_pattern`, and optionally pass `release_approval_verify_command` | Production deploys |
| `EVIDENCE_ACTIVE_CHANGE` | The same | Names the active change key when the branch name can't carry it |
| Org policy | The platform team, through managed deployment | Anything, including loosening a default |
| `/evidence-sdlc:approve KEY SHA`, `evidence approve`, `evidence change set-tier`, `evidence change release` | The human: at the prompt, or at their own terminal (TTY, not inside Claude Code) | Approval, tier changes, release |

An agent can't set any of these environment variables for itself. It can't write
settings files (control plane), and the variables are read from the session's own
environment.

## Rules, in evaluation order

### Writes: Edit, Write, MultiEdit, NotebookEdit, and every Bash write target

The same function (`check_write`) judges Edit and Write paths and every path a Bash
command writes to (REQ-V2G-02). A denial caused by a Bash write is prefixed
`[via Bash: <form>]`. Paths are resolved with `realpath` to a repo-relative form
first (REQ-V2G-03). **Paths outside the repository aren't gated**, except the
user-level control plane.

| # | Rule (audit id) | REQ | Denies | Message gist | Way past |
| --- | --- | --- | --- | --- | --- |
| 1 | `control-plane` (user) | V2G-09 | Writing `~/.claude/settings*.json`, `~/.claude/plugins/**`, `~/.claude.json` or the managed-settings directories | "…is Claude Code or Evidence Chain configuration outside the repository. An agent session may not change the configuration that governs it." | A human edits it |
| 2 | `control-plane` | V2G-09 | Writing `.claude/settings*.json`, `.claude/hooks/**`, `.claude/agents/**`, `.evidence/policy.json`, `.evidence/secrets-allowlist.json`, `.evidence/changes/*/approval.json` or `state.json`, `.evidence/audit/**`, `managed-settings.json` or `.mcp.json` | "…is part of the control plane (settings, policy, approvals, change state or audit log). An agent may not write it." | A human edits it, or runs the `evidence` command that owns it |
| 3 | `read-only-agent` | V2K-03 | Any write by a subagent whose type is in `read_only_agents` | "The <agent> agent is read-only by policy and may not write <path>. Return the proposed change to the main session instead." | The main session writes it |
| 4 | `secret` | V2K-01 | Content that matches a secret pattern (see [Secrets](#secrets)) | "Possible secret in <path>: <rule> on line N (fingerprint …)…" | Load it from the environment. For a false positive, a human allowlists the fingerprint |
| 5 | `self-approval` (approval line) | V2A-01 | Writing an approval line (`Approved by: <name>`, `Approver: …`, `\| Approved by \| … \|`, `Status: approved`) into an `intent`, `spec` or `plan` file. Placeholders like `<name>`, `[ASK]`, `PENDING` and `TBD` are fine | "<path>: approval is not written into planning artifacts. It is recorded only in .evidence/changes/<KEY>/approval.json by a human (`/evidence-sdlc:approve <KEY> <plan-sha>`)…" | The human sends the approve command |
| 6 | `test-weakening` (legacy) | V2G-10 | With `FIX_TASK=1` set by the human: editing a test file that exists at HEAD | "This is a fix task (FIX_TASK=1) and <path> is an existing test. Fix the code, not the test." | Honoured for v1 compatibility. Prefer `--kind fix` |
| — | *ungated → allow* | V2G-03 | — | Docs, `intent/**`, `plan/**`, `.evidence/context/**`, `.evidence/decisions/**`, licence files and the like need no change | — |
| 7 | `no-active-change` | V2G-04 | A source write when neither the branch nor `EVIDENCE_ACTIVE_CHANGE` carries a tracker key | "Writing <path> needs an active change, and none was found (branch <b> carries no tracker key). Create or switch to a branch named with the key…, then run `evidence change start …`" | Branch `feature/KEY-slug`, then `evidence change start` |
| 8 | `no-change-state` | V2S-01 | A key exists, but `.evidence/changes/<KEY>/state.json` doesn't | "…needs change KEY to be started. Run `evidence change start KEY --tier <1\|2\|3> --kind feature\|fix\|chore`…" | Start the change |
| 9 | `missing-artifacts` | V2S-01 | The tier's artifacts are missing (T1: plan; T2: spec and plan; T3: intent, spec and plan) | "…change KEY is Tier N, which requires … Missing: spec.md." | Write them. Artifacts are found at `plan/KEY.md` or `intent/*/<name>.md` with `Tracker: KEY` in the header, or at the paths passed to `change start` |
| 10 | `plan-stub` | V2G-04 | The plan is under 200 characters, has no `## Files claimed` entries, has no `## Order of work`, or still has placeholder claims | "…the plan for KEY (…) is not a real plan yet: plan has no entries under \"## Files claimed\"…" | Write a real plan |
| 11 | `not-approved` | V2A-01 | There is no `approval.json` | "…the plan for KEY has not been approved. Ask a human to review <plan> and send `/evidence-sdlc:approve KEY <sha12>` (or run `evidence approve KEY <sha12>` in their own terminal). An agent cannot approve its own plan." | The human sends `/evidence-sdlc:approve KEY <sha-prefix>` |
| 12 | `approval-stale` | V2A-01 | The plan's sha256 is no longer the one the human approved | "…the plan for KEY changed after it was approved, so the approval no longer applies. A human must re-read it and send `/evidence-sdlc:approve KEY <new sha12>`." | The human re-approves the new hash |
| 13 | `tier-floor` | V2S-02 | The path's policy floor is above the change's tier (for example `**/auth/**` in a Tier 2 change) | "…policy sets a minimum of Tier 3 for this path, but change KEY is Tier 2. A human raises the tier with `evidence change set-tier KEY 3`…" | A human runs `set-tier` at their terminal |
| 14 | `tier3-auto-mode` | V2S-03, LLA-08 | A Tier 3 source edit while `permission_mode` is `bypassPermissions` or `dontAsk` (always), or `acceptEdits` / `auto` unless the server gate is confirmed (2.2.0: `tier3_auto_modes_with_required_gate` on, a signed session, and `verify-range` required on the default branch and pinned to GitHub Actions, read from GitHub) | "…change KEY is Tier 3, which requires per-change human review, but this session is in 'auto' mode… <the missing condition and the owner action>" | Switch to default mode, or the owner pins the check and sets `approval.github_repo` |
| 15 | `outside-claims` | V2G-12 | A path that no glob in the approved plan's `## Files claimed` matches | "…<path> is not in the approved plan's \"Files claimed\" for KEY. Add it to the plan (which voids the approval) and ask for re-approval, or leave the file alone." | Amend the plan and get re-approval |
| 16 | `change-controlled` | V2G-08 | A `change_controlled` path (migrations, CI, infra, audit, signing, crypto, validation) without a valid `CHANGE_TICKET` | "…<path> is under formal change control… A human starts the session with CHANGE_TICKET set to an approved change record matching …" | The human sets `CHANGE_TICKET` |
| 17 | `test-weakening` | V2G-10 | In a `fix` change past `failing-test`, editing or deleting a test file that existed at the recorded `fix_base` commit | "…change KEY is a fix past its failing-test stage, and <path> is a test that existed before the fix. Fix the code, not the test… New test files are allowed." | A human decides the test is wrong. New tests are fine |

Rules 7–17 also apply to `git reset --hard`, `git clean -f` and `git stash pop/apply`.
Those commands are allowed only inside an approved change, with no path (so claims and
floors aren't checked).

### Bash

`check_bash` first scans the whole command text for secrets. Then it applies these
rules to each simple command, and runs every write target through the table above.

| Rule (audit id) | REQ | Denies | Message gist |
| --- | --- | --- | --- |
| Bash writes | V2G-02 | Redirects (`>`, `>>`), `tee`, `cp`, `mv`, `rm`, `install`, `ln`, `touch`, `chmod`/`chown`, `sed -i`, `perl -pi`, `dd of=`, `truncate`, `curl -o path`, `git checkout -- path`, `git restore`, `git rm`, `git mv`. Each target goes through the write rules | "[via Bash: redirect] Writing src/x.py: …" |
| `opaque-write` | V2G-02, USA-07/08 | Writes the engine can't inspect: inline interpreter code that writes files (`python -c` or a python heredoc, `node -e`, ruby, perl); `patch`; `git apply` and `git am`; `curl -O`; archive extraction (`tar`, `unzip` and similar). Also a write to a path computed at run time (`> $OUT`), and running code from a temporary directory (see [Temp-directory paths](#temp-directory-paths)) | "This command modifies files in a way the gates cannot inspect (…). Use the Edit or Write tools…" |
| `self-approval` | V2A-01 | `evidence approve` (except `--github-pr`), `evidence change set-tier` and `evidence change release`, in any form (including `python3 …/evidence …`). Also `gh pr review --approve`, a `gh pr/issue comment` containing `/approve-plan`, and `gh api` calls that submit an APPROVE review or post `/approve-plan` | "Approving a plan (and changing a change's tier) is a human action. Ask the human to run `/evidence-sdlc:approve <KEY> <plan-sha>`…" |
| `git-config` | V2K-02 | `git -c <key>=…` or `git config <key> <value>` for `deny_git_config_keys` (`alias.*`, `core.hooksPath`, `core.sshCommand`, `credential.*`, `include.path`, `filter.*`, …); any `git --config-env` | "`git -c alias.x=…` can run arbitrary programs or change how git authenticates…" |
| `protected-push` | V2G-05 | A push whose **target** ref is protected, from any branch. Forms covered: `HEAD:main`, `+x:main`, `refs/heads/main`, `:main`, `--delete`, `--mirror`, `--all`, `git -C`/`-c`, `env`/`command`/`sudo` wrappers, `/usr/bin/git` | "This push would update main, which is protected. An agent has no route to a protected branch…" |
| `review-agents` | V2S-04 | `git push`, `gh pr create` (and `evidence change advance KEY verified`) for an active change whose tier's required agents have no recorded `agent-completed` run | "Pushing for change KEY (Tier 3) needs these review agents to have run on it first: verifier, security-reviewer, code-reviewer…" |
| `commit-message` | V2G-07 | `git commit` with no message on the command line | "Give the commit message on the command line (-m or -F)…" |
| `commit-key` | V2G-07 | No tracker key in the **message**, or a key different from the active change's. Messages are read from `-m`, `-F file`, `-F -` with a heredoc, and `"$(cat <<'EOF' … EOF)"`; for `--amend --no-edit`, from HEAD | "The commit message carries no tracker key… The key in the branch name alone is not enough." |
| `agent-trailer` | V2A-03 | A message without `Agent-Session: <this session's id>` | "Commits made by an agent must say which session made them. End the commit message with the trailer line: Agent-Session: …" |
| `secret` | V2K-01 | Secrets in the staged diff (plus the working tree for `-a`) or in the commit message | as above |
| `commit-bypass` | IMH-10 | `git commit` with a pathspec, `--only`/`-o`, `--include`/`-i`, `--patch`/`-p`, `--interactive` or `--pathspec-from-file`; `git commit` in the same command as an index-changing git command (`git add … && git commit`); `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY` or `GIT_ALTERNATE_OBJECT_DIRECTORIES` on a command (rule `identity`) | "`git commit` with a pathspec commits files other than the staged index the gates check. Stage … then run a plain `git commit -m …`." |
| `git-config-refused` | IMH-09, USA-10/11 | Any call, when the git config the engine would run with (any scope but `command`, includes followed) sets a key in `deny_git_config_keys`, other than `credential.*` at global or system scope, a `git_config_engine_ignored` key (aliases, editors, pagers, `*tool.*.cmd`) at global or system scope (2.3.0), or an exact `git_allowed_config` value. Two sets: the ignored keys are read only by interactive git, which the engine never runs; `ENGINE_ALWAYS_REFUSED` (in code: `core.fsmonitor`, `core.hooksPath`, `core.sshCommand`, `filter.*`, `diff.*.textconv`, `gpg.*`, `include.path`, `includeIf.*`, `remote.*.url`, `remote.*.pushurl`, `url.*.insteadOf`, `url.*.pushInsteadOf`, …) can make the engine's own git run a program or repoint a remote and is refused at every scope whatever the policy says. An ignored key at local or worktree scope is still refused (the agent can write `.git/config`) | "git config core.fsmonitor (local, file:.git/config) can make git run a command… A human removes it, or the organisation allow-lists the exact value…" |
| `git-unavailable` | IMH-23 | Any call inside a repository git cannot read; a commit whose staged listing or diff git could not produce | "This directory is inside a git repository that git cannot read…" |
| `audit-oversize` | IMH-20 | Any call while an audit log is over 64 MiB (checked by size only) | "Audit log … is larger than the 64 MiB the gates can check in time…" |
| `audit-unwritable` | IMH-06 | Any call while an earlier call's own audit entry could not be written (an open violation) | "An earlier call's audit entry could not be written…" |
| `agent-merge` | V2G-05 | `gh pr merge` (always with `--admin`). `gh api -X PUT/POST/PATCH/DELETE` to `/merge`, `/protection`, `/rulesets`, branch rename or `/git/refs`. `gh api graphql` mutations that merge, auto-merge, add a review, or change protection or refs. `curl`/`wget`/`http`/`xh` with a mutating method or body against `api.github.com` or a GitLab API | "Merging is a human decision in this repository…" / "Mutating a code host's API directly … is not available to an agent session" |
| `check-forgery` | LLA-10 | `gh api` calls that create or update a commit status or check run, or re-run a workflow: POST/PATCH/PUT (also via an `X-HTTP-Method-Override` header), or fields with no method (gh then posts), to `…/statuses/<sha>`, `…/check-runs`, `…/check-suites` or `…/actions/runs|jobs/<id>/rerun*`, matched after percent-decoding and collapsing doubled slashes; `gh run rerun`; the GraphQL `createCheckRun`/`updateCheckRun`/`createCheckSuite` mutations, and any `gh api graphql` whose query is read from a file (`query=@…`) or `--input`. Reading them is allowed | "Creating or updating a commit status or check run from an agent session is not allowed: a required check matched by name could be satisfied that way." |
| `release-approval` | V2G-06 | A deploy tool, recognised by command position, pointed at a production target (a `prod_words` match, case-insensitive), or at a computed target, without a valid `RELEASE_APPROVAL`. The tools: `kubectl`/`oc` mutating verbs, `helm install/upgrade/rollback`, `terraform`/`tofu apply/destroy`, `pulumi up`, `cdk`/`serverless`/`sam`/`firebase`/`wrangler deploy`, `aws`/`gcloud`/`az` deploy verbs, `gh workflow run deploy*`, make/npm/yarn deploy targets, and scripts named deploy/release/promote/rollout/ship. Plain text such as `grep production` never triggers it | "`kubectl apply` names a production target (prod-eu). Production changes need a release authorization… The agent cannot supply it." |

### Secrets

`secretscan.py` checks for AWS, GitHub, GitLab, Slack, Stripe, Google, Anthropic,
OpenAI, npm, SendGrid and Twilio tokens; private-key blocks; JWTs; connection strings
with passwords; Azure storage keys; and high-entropy credential assignments.
Placeholders and environment references are ignored. The value is never echoed; only a
fingerprint is shown. To allowlist a false positive, a human adds the fingerprint to
`.evidence/secrets-allowlist.json` (which is control plane).

### Approval (REQ-V2A-01)

There are three human-only channels:

1. **The prompt.** The human sends `/evidence-sdlc:approve KEY <sha-prefix>`. The
   `UserPromptSubmit` hook matches the raw prompt text (`evidence approve KEY SHA`
   also works) and writes `approval.json`, with the approver taken from
   `git user.email` and method `prompt`. A missing or stale hash is refused, with the
   current hash shown.
2. **The terminal.** `evidence approve KEY` in the human's own terminal. It needs
   `/dev/tty`, refuses inside Claude Code, and the human types the first 8 characters
   of the sha.
3. **GitHub.** `evidence approve KEY --github-pr N` records an APPROVED review, or a
   `/approve-plan <sha12>` comment, by an allowed login other than the PR author. The
   PR's branch must carry the key, the plan blob at the PR head must equal the local
   plan, and the approver must not be the PR author. Agents may run this one. Since 2.1.0
   the repository must be pinned in policy (`approval.github_repo`); `gh` is always called
   with `--repo`, never left to resolve it from the working copy's remotes (REQ-IMH-24).

This local record is evidence, not the merge decision: `verify-range` requires a code-owner
review on the PR's head commit whatever `approval.json` says (see "Where the authority is").

### Audit (REQ-V2A-02)

Each session writes `.evidence/audit/<session>.jsonl`. Every entry holds `prev` and
the sha256 `hash` of its canonical JSON, and records the timestamp, session, user,
tool, path or command, key, agent type and id, permission mode, and engine version.
There are entries for every Edit, Write, MultiEdit, NotebookEdit and Bash call, every
deny (with its rule and reason), and every agent dispatch, completion and failure.
Approvals go to `.evidence/audit/approval.jsonl`. `evidence audit verify` reports a line that was altered or removed.
Since 2.1.0 it also reports a replayed line (a repeated entry hash) and, in a session's log, a
line belonging to another session (REQ-IMH-11).
`evidence metrics` summarises denials by rule and self-approval attempts.

### Engine git and the integrity monitor (2.1.0, ADR-0003)

- **Engine git is neutralised.** Every git and `gh` process the engine starts goes through
  `state.run_git` / `run_gh`: `core.fsmonitor`, hooks, pager, attributes file, external diff and
  textconv are switched off, attributes are read from the empty tree, and the child's
  environment has no `GIT_*` variables and no signing key (REQ-IMH-09, 22, 24). The allow-list
  of subprocess call sites is enforced by an AST test.
- **The monitor never follows a link.** Control-plane files are listed, restored and removed
  through directory handles opened with `O_NOFOLLOW`. A symlink or non-file at a control-plane
  path (audit logs included) is a violation, and nothing it points to is touched (REQ-IMH-01).
  A non-file at a violations path counts as an open violation (REQ-IMH-02).
- **Snapshots** in the temp directory are written and read the same way, with a 4 MiB cap. Their
  protection is the HMAC signature and the binding to the call's `tool_use_id`; a link, non-file or
  oversize snapshot counts as altered (REQ-IMH-08).
- **Also violations:** a changed type, mode, owner or identity of `.evidence`, `.evidence/audit`,
  `.evidence/changes` or `.evidence/violations` (REQ-IMH-05); a deleted untracked file the gates
  would have denied (REQ-IMH-07); an audit log whose earlier bytes changed, or a new log that
  doesn't verify (REQ-IMH-20); git failing after the call (`git-unavailable`: the control-plane
  restore and audit checks still run, REQ-IMH-23).
- **Permission grants are kept.** The hook runs before Claude Code's permission prompt, so a
  "don't ask again" answer writes `.claude/settings.local.json` while the call is in flight. When
  the only change is new `permissions.allow` entries, the file is kept and a `permission-grant`
  audit entry is written. Since 2.2.0 more edits are kept (see below); anything else is restored.
- A pre hook that runs past 25 seconds denies the call; a post hook that does records an
  `integrity-timeout` violation (the hook limit is 30).

### The local layer is advisory in practice (2.2.0, ADR-0005)

The local layer gains no authority in 2.2.0; it stops costing a human round trip for events that
are not the agent's doing or that it has already undone.

- **A verified undo is closed at birth.** When the monitor restores a changed control-plane file
  and the re-read equals the snapshot, or removes a created file or planted symlink and the path
  is gone, the violation is written `open: false`, `resolved: "restored"`, `resolved_at`, and
  logged as an `integrity-violation` audit event with `resolved`. It blocks neither push/PR nor
  source edits, and needs no `clear-violations`; the post-call note says the change was undone and
  there is nothing to clear. The record stays, and `verify-range` shows each one to the code
  owner (rule 5 `NOTE:`). Only the pairs in `AUTO_RESOLVABLE` qualify: `control-plane` restored or
  removed, `control-plane-symlink` removed.
- **Everything else stays open and blocks as in 2.1.0:** an unsigned-mode `recorded`, a restore
  whose write fails or whose re-read differs, `control-plane-removal-refused`, `audit-tamper`,
  `hidden-change`, `evidence-dir-changed`, `git-unavailable`, `git-dir-replaced`, the
  `integrity-snapshot-*`, `integrity-timeout`, `integrity-check-error` and `audit-unwritable`
  entries, and any gated path written by a program the gates could not see.
- **The per-session cap.** Once a session has `auto_resolve_max_per_session` (default 3)
  entries closed at birth in the change's or branch's record, the next restored change is open
  and the note says why. `0` disables closing at birth. The org policy sets it; a repository
  policy may only lower it.
- **Config edits are judged by effect, not author** (the engine cannot tell the human from the agent):
  - `.claude/settings.local.json` is kept, with a `config-change` audit event, when every
    difference is an `allow` entry added or removed, a `deny` or `ask` entry added, an
    `additionalDirectories` entry removed, or a top-level key in `local_settings_kept_keys`
    (default `model`, `outputStyle`). A pure allow addition is still a `permission-grant`. A newly
    created file is kept only when it holds nothing but `permissions.allow` entries; any other new
    file is removed like any created control-plane file. Everything else is restored, including an
    `additionalDirectories` entry added: `hooks`, `disableAllHooks`, `env`,
    `statusLine`, `apiKeyHelper`, `enabledPlugins`, MCP keys, `permissions.defaultMode`, a deny or
    ask rule removed, invalid JSON, a BOM.
  - A file in `user_config_not_charged` (the managed-settings files and `evidence-policy.json`
    under `/Library/Application Support/ClaudeCode/` and `/etc/claude-code/`) changed during a call
    is logged as `user-config-changed` (path, old and new hash, owner uid, mode) and is not a
    violation, **only if** before and after the call it is not owned by the hook's user and
    neither it nor its directory is writable by that user. A listed file the user could have
    written is still `hidden-change`.
  - `~/.claude.json` (and `$CLAUDE_CONFIG_DIR/.claude.json`) is charged only when its security
    projection changes: the top-level `mcpServers` and, under `projects.*`, the keys in
    `claude_json_security_keys`. Claude Code's bookkeeping rewrites are ignored; a file that
    becomes invalid, missing or over 64 MiB is `hidden-change`.
- **Tier 3 auto modes follow the server gate.** A Tier 3 edit in a mode listed in
  `tier3_gate_allowed_modes` (default `acceptEdits`, `auto`) is allowed when
  `tier3_auto_modes_with_required_gate` is on, the session is signed, and the engine reads from
  GitHub, through `gh` pinned to `approval.github_repo`, that `ci_gate_check` (`verify-range`) is
  a required status check on the default branch **pinned to the GitHub Actions app**
  (`ci_gate_app_id`, `checks[].app_id` in branch protection or `integration_id` in a ruleset).
  "Any source", another app, a missing check, `gh` failing or timing out, non-JSON output or an
  empty `github_repo` all mean not confirmed, and the denial names which. The gate also requires:
  the repository's `origin` remote is `approval.github_repo` on github.com (https or ssh, `.git`
  and case ignored), read from the repository's own config only: exactly one local
  `remote.origin.url`, `remote.origin.pushurl` absent or equal to it, no `remote.origin.url` or
  `pushurl` at global or system scope, and no `url.*.insteadOf` / `pushInsteadOf` rewrite (setting
  any of these keys with `git config` or `git -c`, at any scope, is denied as `remote-change`, and `git config --rename-section`/`--remove-section`/`--edit` as `git-config-section`); `gh` is the org policy's `ci_gate_gh_path` or the first `gh` on PATH that the
  session's user could not have written (neither it nor its directory writable by the user), and
  takes its token from `gh auth token --hostname github.com` (the only call made with the user's gh
  configuration), then runs every `gh api` call with a root-owned empty `GH_CONFIG_DIR` (`/var/empty`),
  `GH_TOKEN`, `GH_HOST=github.com` and no other `GH_*`/`GITHUB_*`, so nothing in the user's gh
  configuration applies; the checkout's real path is in the org policy's
  `approval.github_repo_roots`; and no `include.path`/`includeIf.*` is set and
  `remote.pushDefault`/`branch.*.pushRemote` name only `origin`. With
  `ci_gate_require_enforce_admins`, a check required only by a ruleset does not confirm, because
  the rules endpoint does not show a ruleset's bypass actors. The result is cached in
  a signed file in the temp directory (900 s for a confirmation, 60 s for a failure); an
  unsigned, altered, expired or linked cache is ignored. A `tier3-auto-mode-allowed` audit event
  records the evidence each time the cache is filled. `bypassPermissions` and `dontAsk` stay
  denied.

## Advisory hooks (never deny)

| Hook | Plugin | Does |
| --- | --- | --- |
| `preflight.sh` | evidence-sdlc | At SessionStart, checks for Python 3.8+, the engine files and the default policy, and says `Preflight OK` or `PREFLIGHT FAILED` |
| `sensor.py` (via `post`) | evidence-sdlc | Flags a placeholder `## Areas of concern` or `## Files claimed`, a Tier 2/3 plan without a CHECKPOINT, or a new skill with no eval case |
| `require-repo-profile.sh` | evidence-discovery | At SessionStart, says whether `.evidence/context/` exists and counts unresolved `[ASK]`s |
| `check-test-plan-rows.py` | evidence-quality | At SessionStart, checks the active plans for test-plan rows. Skipped silently without `python3` |

## Tests

| Suite | Covers |
| --- | --- |
| `python3 plugins/evidence-sdlc/scripts/tests/engine-tests.py [-v] [-k text]` | Over 200 cases. Each is run exactly as Claude Code runs the hook (JSON on stdin to `hook.py`, in a throwaway git repo), and case labels start with the REQ ID (`V2G-02 …`, `V2S-04 …`). Every v1 audit probe is a case |
| `python3 plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py` | `evidence change / approve / audit / metrics` |

To find the case for a rule, run `engine-tests.py -v -k V2G-05`. `evidence doctor`
also runs a live canary against the shipped engine: in a throwaway repo, it must deny
`src/__canary__.py` and allow `docs/__canary__.md`.

## Temp-directory paths

Since 2.3.0 (PILOT-60, REQ-USA-07/08) a path under a temporary directory (`/tmp/`, `/private/tmp/`,
`/var/tmp/`, `/var/folders/`, `$TMPDIR`, compared as real paths with a trailing `/`) is judged as a
**path**, like any other, when the program only reads, lists or creates it:
`cat`, `head`, `tail`, `wc`, `ls`, `stat`, `file`, `du`, `mkdir`, `rmdir`, `rm`, `touch`, `tee`,
`mktemp`, `grep`, `egrep`, `fgrep`, `rg`, `uniq`, `cut`, `tr`, `diff`, `cmp`, `md5sum`,
`sha256sum`, `shasum`, `jq`, `basename`, `dirname`, `realpath`, `readlink`, `echo`, `printf`, `test`,
`[`, and `cp` and `mv` with the temp path as the **destination** only (`cp src/app.py /tmp/app.bak`).
Their writes are still judged by the usual rules (claims, control plane, secrets). The relaxation
never applies to a command that has a process substitution (`<(…)`, `>(…)`) anywhere, or any write
(a redirect, `tee`, a copy's destination) that is inside the repository, opaque or computed at run
time: `cat /tmp/x > src/app.py` and `cat /tmp/x | tee -a src/app.py` are denied.

These stay denied as `opaque-write`, because they run code the gates never saw written, or carry
temp content into the repository:

- running a script from a temp directory (`python3 /tmp/x.py`, `bash /tmp/x.sh`, `source /tmp/x`,
  `make -f /tmp/Makefile`, `go run /tmp/x.go`, `awk -f`, `sed -f`), or any temp path given to a
  program not on the list. Since the PILOT-60 review, `sort` (`--compress-program`), `curl` (`-K`),
  `wget` (`-e`) and `chmod` (it makes a temp file executable) are not on it, so `sort /tmp/a`,
  `curl -o /tmp/x.json …` and `chmod +x /tmp/x` are denied;
- a temp path given to a code-running option: `rg --pre`, `sort --compress-program`,
  `curl -K`/`--config`, `wget -e`/`--execute`/`--config` (`--opt value`, `--opt=value` and its
  abbreviations, and `-Kvalue` alone or in a cluster such as `-qK/tmp/cfg`);
- `cp` or `mv` with a temp **source** (`cp /tmp/x src/app.py`, `cp /tmp/a /tmp/b`), and any `cp`/`mv`
  with `-t` in any form (`-t`, a cluster such as `-rt`, `--target-directory`, `--target`).

A path written as the literal `$TMPDIR/…` is computed at run time: a write to it
(`cp src/app.py $TMPDIR/app.bak`) is denied as such. Write the expanded path instead.

The deny message adds: "To read or list a temp file, use cat, ls or the Read tool."

**Sandbox note:** in the Claude Code sandbox on macOS a bare `mktemp` fails ("mkstemp failed …
Operation not permitted") because it ignores `TMPDIR`. The gate allows it; use the sandbox-safe form
`mktemp "$TMPDIR/x.XXXXXX"` (or `mktemp -d "$TMPDIR/x.XXXXXX"`).
