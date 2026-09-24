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
| 14 | `tier3-auto-mode` | V2S-03 | A Tier 3 source edit while `permission_mode` is `bypassPermissions`, `acceptEdits`, `dontAsk` or `auto` | "…change KEY is Tier 3, which requires per-change human review, but this session is in 'acceptEdits' mode." | Switch to default mode |
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
| `opaque-write` | V2G-02 | Writes the engine can't inspect: inline interpreter code that writes files (`python -c` or a python heredoc, `node -e`, ruby, perl); `patch`; `git apply` and `git am`; `curl -O`; archive extraction (`tar`, `unzip` and similar). Also a write to a path computed at run time (`> $OUT`) | "This command modifies files in a way the gates cannot inspect (…). Use the Edit or Write tools…" |
| `self-approval` | V2A-01 | `evidence approve` (except `--github-pr`), `evidence change set-tier` and `evidence change release`, in any form (including `python3 …/evidence …`). Also `gh pr review --approve`, a `gh pr/issue comment` containing `/approve-plan`, and `gh api` calls that submit an APPROVE review or post `/approve-plan` | "Approving a plan (and changing a change's tier) is a human action. Ask the human to run `/evidence-sdlc:approve <KEY> <plan-sha>`…" |
| `git-config` | V2K-02 | `git -c <key>=…` or `git config <key> <value>` for `deny_git_config_keys` (`alias.*`, `core.hooksPath`, `core.sshCommand`, `credential.*`, `include.path`, `filter.*`, …); any `git --config-env` | "`git -c alias.x=…` can run arbitrary programs or change how git authenticates…" |
| `protected-push` | V2G-05 | A push whose **target** ref is protected, from any branch. Forms covered: `HEAD:main`, `+x:main`, `refs/heads/main`, `:main`, `--delete`, `--mirror`, `--all`, `git -C`/`-c`, `env`/`command`/`sudo` wrappers, `/usr/bin/git` | "This push would update main, which is protected. An agent has no route to a protected branch…" |
| `review-agents` | V2S-04 | `git push`, `gh pr create` (and `evidence change advance KEY verified`) for an active change whose tier's required agents have no recorded `agent-completed` run | "Pushing for change KEY (Tier 3) needs these review agents to have run on it first: verifier, security-reviewer, code-reviewer…" |
| `commit-message` | V2G-07 | `git commit` with no message on the command line | "Give the commit message on the command line (-m or -F)…" |
| `commit-key` | V2G-07 | No tracker key in the **message**, or a key different from the active change's. Messages are read from `-m`, `-F file`, `-F -` with a heredoc, and `"$(cat <<'EOF' … EOF)"`; for `--amend --no-edit`, from HEAD | "The commit message carries no tracker key… The key in the branch name alone is not enough." |
| `agent-trailer` | V2A-03 | A message without `Agent-Session: <this session's id>` | "Commits made by an agent must say which session made them. End the commit message with the trailer line: Agent-Session: …" |
| `secret` | V2K-01 | Secrets in the staged diff (plus the working tree for `-a`) or in the commit message | as above |
| `agent-merge` | V2G-05 | `gh pr merge` (always with `--admin`). `gh api -X PUT/POST/PATCH/DELETE` to `/merge`, `/protection`, `/rulesets`, branch rename or `/git/refs`. `gh api graphql` mutations that merge, auto-merge, add a review, or change protection or refs. `curl`/`wget`/`http`/`xh` with a mutating method or body against `api.github.com` or a GitLab API | "Merging is a human decision in this repository…" / "Mutating a code host's API directly … is not available to an agent session" |
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
   plan, and the approver must not be the PR author. Agents may run this one.

### Audit (REQ-V2A-02)

Each session writes `.evidence/audit/<session>.jsonl`. Every entry holds `prev` and
the sha256 `hash` of its canonical JSON, and records the timestamp, session, user,
tool, path or command, key, agent type and id, permission mode, and engine version.
There are entries for every Edit, Write, MultiEdit, NotebookEdit and Bash call, every
deny (with its rule and reason), and every agent dispatch, completion and failure.
Approvals go to `.evidence/audit/approval.jsonl`. `evidence audit verify` reports a line that was altered or removed.
`evidence metrics` summarises denials by rule and self-approval attempts.

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
