# Gates reference

This is the standalone, per-script reference for every hook registered across the three
Evidence Chain plugins (`evidence-discovery`, `evidence-quality`, `evidence-sdlc`).
README.md's ["The gates"](../README.md#the-gates) table and diagram give the
seven-gate cross-cutting view; SECURITY.md's ["Using this safely"](../SECURITY.md#using-this-safely)
section explains the fail-open threat model these scripts operate under (hook execution
failures are treated as **allow** by the runtime, which is why every hook below is
invoked as `bash ${CLAUDE_PLUGIN_ROOT}/scripts/<script>.sh` rather than relying on the
script's own execute bit). This document does not repeat that framing beyond what's
needed for context — it exists to enumerate, for all 11 scripts referenced by the three
`hooks.json` files, exactly what event triggers each one, what it reads, its decision
logic including edge cases actually present in the code, any bypass/environment
variable, and the literal message a reader will see.

Three of the eleven scripts are advisory only (`require-repo-profile`,
`check-test-plan-rows`, `audit-log`, plus `preflight` and `session-context` which also
never deny) — they add context or log, but cannot block a tool call. The remaining six
can return `permissionDecision: "deny"` (or, in `production-gate`'s case, exit 2) and
stop the tool call.

---

## evidence-discovery

### `require-repo-profile.sh`

| Field | Detail |
| --- | --- |
| Registered under | `SessionStart` (unconditional — runs at the start of every session) |
| Matcher / `if` | None; fires every session start |
| Input read | Nothing from the hook payload — it checks the filesystem directly (`.evidence/context/stack.md`, and `.evidence/context/*.md` for `[ASK]` counts) |
| Decision logic | Never denies anything — it only ever emits `additionalContext`. If `.evidence/context/stack.md` does not exist, it tells the session no repository profile exists and to run stack-discovery/toolchain-discovery/design-system-discovery first. If the file exists, it counts occurrences of the literal string `[ASK]` across all `.evidence/context/*.md` files and reports that count, adding that an `[ASK]` in an area the change depends on is a blocker to raise with a human. |
| Env var / bypass | None. There's no way to silence this — it's purely informational and always runs. |
| Message text | Missing profile: *"No repository profile exists at .evidence/context/stack.md. The technology stack, deployment stack, toolchain and design system for this repository have not been established. Run stack-discovery, toolchain-discovery and design-system-discovery before planning any change. Do not assume a framework, runtime, datastore or deployment target."* Present profile: *"Repository profile present at .evidence/context/. Read stack.md, deployment.md, toolchain.md and design-system.md before planning. Unresolved [ASK] items: N. An [ASK] in an area this change depends on is a blocker — ask the human rather than assuming."* |

---

## evidence-quality

### `require-issue-key.sh`

| Field | Detail |
| --- | --- |
| Registered under | `PreToolUse`, matcher `Bash`, gated further by `if: "Bash(git commit *)"` |
| Input read | `tool_input.command`; also shells out to `git rev-parse --abbrev-ref HEAD` for the branch name |
| Decision logic | First re-checks that `git commit` actually appears at a command-invocation position (start of line, or right after `;`, `&`, `|`, backtick, or `(`) rather than merely as a substring anywhere in the command text — this is a deliberate fix for a prior false positive where a heredoc or `echo` merely *mentioning* "git commit" in a string was denied as though it were a real commit. If the command isn't a real `git commit` invocation, it exits 0 (allow) immediately. Otherwise it looks for a tracker-key pattern in either the commit command text or the current branch name; if found in either place, allow. If found in neither, deny. |
| Env var / bypass | `EVIDENCE_ISSUE_KEY_PATTERN` — overrides the regex used to recognize a tracker key. Default: `[A-Z][A-Z0-9]+-[0-9]+` (e.g. `PROJ-123`). Comment notes the pattern is meant to come from the repository profile/project settings, not be hardcoded here. |
| Message text | *"No tracker issue key found in the commit message or the branch name. Every commit must carry the key (pattern: &lt;pattern&gt;) so the traceability chain from requirement to test to evidence holds. If no issue exists for this work, create one first — do not add the key retrospectively."* |

### `check-test-plan-rows.sh`

| Field | Detail |
| --- | --- |
| Registered under | `SessionStart` (unconditional) |
| Matcher / `if` | None |
| Input read | Nothing from the hook payload — reads the filesystem: the first of `plan.md`, `*/plan.md`, or `intent/*/plan.md` (in that priority order via `ls ... | head -1`) |
| Decision logic | Advisory only — can never deny (it's a `SessionStart` hook and only ever emits `additionalContext` or exits silently). If no plan file is found, or the plan has no `REQ-*-NNN`-style requirement IDs, it exits 0 silently. Otherwise, for each unique requirement ID found, it checks whether any line containing that ID also contains one of `test`, `case`, `spec`, or a TestRail-style `C<number>` reference (case-insensitive). Any requirement ID with no such line is reported as missing test coverage. The script's own comment states this is deliberately advisory, not blocking, because "blocking here would fire mid-thought during planning." |
| Env var / bypass | None — always advisory, nothing to bypass. |
| Message text | *"The plan has requirement IDs with no named test: &lt;list&gt;. A requirement with no test is an incomplete plan. Apply the test-strategy skill and add rows before implementation is reported complete."* |

---

## evidence-sdlc

### `gate-plan-exists.sh`

| Field | Detail |
| --- | --- |
| Registered under | `PreToolUse`, matcher `Edit\|Write\|MultiEdit` |
| Matcher / `if` | Matcher only; no additional `if` — runs on every Edit/Write/MultiEdit call, then exempts specific paths in code |
| Input read | `tool_input.file_path` or `tool_input.path`; also `git rev-parse --abbrev-ref HEAD` for the branch |
| Decision logic | Exits 0 immediately (no path to check) if the tool call carries no path. Exempts (never gates) paths matching `*/intent/*`, `*/docs/*`, `*intent.md`, `*spec.md`, `*plan.md`, `plan/*.md`, `*CLAUDE.md`, `*.claude/*`, `*/validation/*`, `*/tmp/*`, `*.log`. For everything else, it decides which paths count as "source": if `EVIDENCE_SOURCE_GLOB` is set, only paths matching that glob are gated (everything else allowed); if unset, it gates anything that is *not* one of `*.md`, `*.txt`, `*.json`, `*.yaml`, `*.yml`, `*.csv`, `*.lock` (a broad "assume it's code" default). For a gated path, it allows the edit if any of: `plan.md` exists at repo root, a `*/plan.md` glob matches, an `intent/*/plan.md` glob matches, OR a tracker key parsed out of the current branch name (via `EVIDENCE_ISSUE_KEY_PATTERN`, same default as `require-issue-key.sh`) has a matching `plan/<KEY>.md` file. Otherwise it denies. Note: the branch-keyed `plan/<KEY>.md` form only satisfies the gate if that key is actually present in the current branch name — a session cannot point at a plan for a different piece of work. |
| Env var / bypass | `EVIDENCE_SOURCE_GLOB` — restricts which paths are treated as "source" and therefore gated (unset = broad default gating everything but common non-code extensions). `EVIDENCE_ISSUE_KEY_PATTERN` — same tracker-key pattern used by `require-issue-key.sh`, used here to extract the branch key for the namespaced `plan/<KEY>.md` lookup. |
| Message text | *"No plan.md found (checked plan.md, */plan.md, intent/*/plan.md, and plan/&lt;tracker-key&gt;.md for the current branch). Run the codebase-grounded-planning skill in plan mode and commit an approved plan before editing source. See the Evidence Chain handbook."* |

### `protect-validated-paths.sh`

| Field | Detail |
| --- | --- |
| Registered under | `PreToolUse`, matcher `Edit\|Write\|MultiEdit` |
| Input read | `tool_input.file_path` or `tool_input.path` |
| Decision logic | Exits 0 if no path. Splits the path on `/` and checks each **path segment** (not substring) against an exact-match list: `migrations`, `infra`, `terraform`, `audit`, `signing`, `crypto`, `validation`. If none of the path's segments match exactly, exits 0 (allow) — this segment-exact-match approach is a deliberate fix noted in the script's own comment for a prior bug where substring globs wrongly caught directories like `cache-invalidation/` (contains "validation") or `test-infra/` (contains "infra"), while also missing root-level paths like `audit/report.pdf` that lacked a leading slash. If a segment matches, the path is "protected": if `CHANGE_TICKET` is set, the tool call is **allowed** but annotated with `additionalContext` naming the ticket and reminding that the compliance-reviewer agent must run before the PR opens. If `CHANGE_TICKET` is unset, it **denies**. |
| Env var / bypass | `CHANGE_TICKET` — set to an approved change record reference to allow edits under a protected path; its value is echoed back into the allow-path's `additionalContext`. |
| Message text (deny) | *"&lt;path&gt; is under formal change control (migrations, infrastructure, audit trail, signing, crypto, or validation assets). Set CHANGE_TICKET to an approved change record before editing, or route this through the change board."* Message text (allow-with-context): *"Editing change-controlled path &lt;path&gt; under ticket &lt;ticket&gt;. The change record must reference this ticket and the compliance-reviewer agent must run before this PR is opened."* |

### `block-test-weakening.sh`

| Field | Detail |
| --- | --- |
| Registered under | `PreToolUse`, matcher `Edit\|Write\|MultiEdit` |
| Input read | `tool_input.file_path` or `tool_input.path` |
| Decision logic | This gate is **entirely inert unless `FIX_TASK=1` is set** — it exits 0 immediately otherwise, regardless of path (line 7: `[ "${FIX_TASK:-0}" != "1" ] && exit 0`). When `FIX_TASK=1`, it checks the file's basename against test-name patterns (`test_*`, `*_test.*`, `*.test.*`, `*.spec.*`) as a prefix/pattern match on the basename only, and separately checks whether any exact path segment is `tests`, `__tests__`, or `qa`. If either matches, it denies; otherwise allows. The script's own comment documents a prior bug fix here too: the basename check requires `test_` as a genuine prefix (not substring), since a bare substring check previously false-matched ordinary files like `latest_migration.py` or `fastest_path.py`; and directory checks are exact segments without requiring a leading slash, fixing a prior miss on root-level `tests/helpers.py`. |
| Env var / bypass | `FIX_TASK` — must be set to exactly `1` to activate this gate at all. Comment: intended "for bug-fix sessions where the failing test is written first," so the agent fixing the bug cannot then edit the test that proves the fix. |
| Message text | *"This is a fix task (FIX_TASK=1). The failing test was committed first and proves the bug. Fix the code, not the test. If the test itself is genuinely wrong, stop and say so — a human decides that."* |

### `block-protected-branch-push.sh`

| Field | Detail |
| --- | --- |
| Registered under | `PreToolUse`, matcher `Bash`, gated further by `if: "Bash(git push *)"` |
| Input read | `tool_input.command`; `git rev-parse --abbrev-ref HEAD` for branch |
| Decision logic | First re-verifies (same anti-false-positive technique as `require-issue-key.sh`) that `git push` appears at a genuine command-invocation position, not merely as text inside the command (e.g. an `echo` mentioning "git push" does not trigger it). If it's a real push, checks the current branch name against `main`, `master`, `release`, `release/*`, `hotfix/*`; any other branch is allowed. On a match, denies unconditionally — there is **no environment-variable bypass** for this one. |
| Env var / bypass | None. Comment: "Branch protection is the real control; this stops the attempt earlier and explains why" — i.e. this is a UX/defense-in-depth layer in front of actual server-side branch protection, not the sole enforcement. |
| Message text | *"Direct push to &lt;branch&gt; is not available to an agent session. Open a pull request; a human code owner approves. The agent that wrote the change has no route to approve it. This is a segregation-of-duties control, not a preference."* |

### `production-gate.sh`

| Field | Detail |
| --- | --- |
| Registered under | `PreToolUse`, matcher `Bash`, gated further by `if: "Bash(*deploy*)"` |
| Input read | `tool_input.command` |
| Decision logic | Note the two-stage filter: the `hooks.json` `if` condition only requires the substring `deploy` anywhere in the command for the script to run at all; the script itself then applies a second, stricter check — it only acts if `prod` or `production` appears as a **whole word** (bounded by non-letters or string edges) in the command, via a bash regex. This is a documented fix for a prior bug where a substring glob (`*prod*`) false-triggered on words merely containing "prod" (`reproduce`, `product`, `reproducible`, `byproduct`). So a plain `./deploy.sh staging` never reaches the whole-word check's positive branch and is allowed; a command mentioning `production` does. If the whole-word check doesn't match, exits 0 (allow). If it matches, allows only if `RELEASE_APPROVAL` is set (non-empty); otherwise denies. |
| Env var / bypass | `RELEASE_APPROVAL` — set to the release manager's approval reference to allow the deploy through. |
| **Mechanism difference** | Unlike every other deny in this framework, this script does **not** emit JSON with `permissionDecision`. It writes a plain message to stderr and calls `exit 2`, which Claude Code's hook protocol treats as a blocking failure. Anyone auditing gates by grepping for `permissionDecision: "deny"` will miss this one. |
| Message text | *"Production deploys require a named release authorization. Set RELEASE_APPROVAL to the release manager's approval reference. The validation package for this release must be signed off by QA/RA first."* (written to stderr) |

### `audit-log.sh`

| Field | Detail |
| --- | --- |
| Registered under | `PostToolUse`, matcher `Edit\|Write\|MultiEdit`, `async: true` |
| Input read | `tool_input.file_path` or `tool_input.path` (defaults to the literal string `"unknown"` if absent); `session_id`; `$USER` from the environment |
| Decision logic | Never allows or denies anything — it runs after the tool call has already happened (`PostToolUse`) and is fire-and-forget (`async: true`). It creates `.claude/logs/` if needed and appends one tab-separated line per edit: UTC timestamp, session ID, `$USER` (or `"unknown"`), and the file path. Comment: this is "a convenience record for engineers; the OpenTelemetry export and git history remain the systems of record" — i.e. it is explicitly not the authoritative audit trail. |
| Env var / bypass | None; nothing to bypass since it never blocks. |
| Message text | None — it produces no hook output at all (just the log line on disk). |

### `preflight.sh`

| Field | Detail |
| --- | --- |
| Registered under | `SessionStart` (unconditional, runs before `session-context.sh` in the same hook group) |
| Input read | Nothing from the hook payload. Checks: whether `jq` resolves on `PATH`; whether every `*/scripts/*.sh` file under the plugins directory (resolved relative to `CLAUDE_PLUGIN_ROOT`, falling back to `${BASH_SOURCE[0]%/*}/..` if that var is unset) is readable; whether `.evidence/context/stack.md` exists (informational only). |
| Decision logic | This is the meta-gate that checks the other gates' environment (per its own comment: "Verifies the environment every other gate script in this framework depends on"). It is written using bash builtins only, deliberately avoiding `cat`/`dirname`/`sed`/`tr`/`find`, because a PATH so stripped that coreutils don't resolve is exactly the fail-open scenario it exists to catch and report loudly. **It never sets `permissionDecision`; it only ever emits `additionalContext`, even when it detects a failure** — so a broken environment is surfaced as a strongly-worded warning in session context, not as a blocked action. If `jq` itself is missing, it falls back to hand-built (non-jq) JSON output using string escaping, since jq isn't available to build normal JSON output. |
| Env var / bypass | None to change its behavior; it reads `CLAUDE_PLUGIN_ROOT` only to locate the plugin tree, not as a toggle. |
| Message text (failure) | *"PREFLIGHT FAILED: &lt;failure reasons joined with `; `&gt;Gates may not be enforcing. Do not make source changes until this is fixed. &lt;profile note&gt;"* — failure reasons include e.g. *"jq is not resolvable on PATH -- every gate script shells out to jq to read tool input and emit its decision; without it, gates cannot run at all"* and *"unreadable gate script(s), so they cannot execute: &lt;paths&gt;"*. Message text (success): *"Preflight OK: jq resolves on PATH and all gate scripts are readable. &lt;profile note&gt;"* |

### `session-context.sh`

| Field | Detail |
| --- | --- |
| Registered under | `SessionStart` (unconditional, runs after `preflight.sh` in the same hook group) |
| Input read | Nothing from the hook payload. Runs `git rev-parse --abbrev-ref HEAD` for the branch; looks for the first of `plan.md`, `*/plan.md`, `intent/*/plan.md` via `ls ... | head -1`; reads `CHANGE_TICKET` from the environment. |
| Decision logic | Purely informational — always emits `additionalContext` summarizing branch, plan file found (or `"none"`), and change ticket (or `"none"`), plus a one-line recap of what's gated on what. **Edge case**: unlike `gate-plan-exists.sh`, this script's plan lookup does **not** check the namespaced `plan/<TRACKER-KEY>.md` form. In a concurrent-worktree session using only a keyed plan file, `gate-plan-exists.sh` will correctly allow edits, but `session-context.sh` will still report the plan as `"none"` to the session — a cosmetic inconsistency between what's reported and what's actually enforced. |
| Env var / bypass | Reads `CHANGE_TICKET` for display only; does not gate on it. |
| Message text | *"Evidence Chain session. Branch: &lt;branch&gt;. Approved plan on disk: &lt;plan or 'none'&gt;. Change ticket in environment: &lt;ticket or 'none'&gt;. Source edits are gated on an approved plan.md; migrations, infrastructure, audit, signing, crypto and validation paths are gated on a change ticket; production deploys are gated on a release authorization."* |

---

## Summary table

| Script | Plugin | Event | Bypass / env var |
| --- | --- | --- | --- |
| `require-repo-profile.sh` | evidence-discovery | SessionStart | None (advisory only) |
| `require-issue-key.sh` | evidence-quality | PreToolUse (Bash, `git commit *`) | `EVIDENCE_ISSUE_KEY_PATTERN` (changes the required key regex; presence of a matching key in commit or branch satisfies it) |
| `check-test-plan-rows.sh` | evidence-quality | SessionStart | None (advisory only) |
| `gate-plan-exists.sh` | evidence-sdlc | PreToolUse (Edit\|Write\|MultiEdit) | `EVIDENCE_SOURCE_GLOB` (narrows what counts as gated source); `EVIDENCE_ISSUE_KEY_PATTERN` (for the `plan/<KEY>.md` branch lookup); path exemptions for docs/intent/spec/plan/CLAUDE.md/.claude/validation/tmp/log |
| `protect-validated-paths.sh` | evidence-sdlc | PreToolUse (Edit\|Write\|MultiEdit) | `CHANGE_TICKET` (allows edits to migrations/infra/terraform/audit/signing/crypto/validation path segments) |
| `block-test-weakening.sh` | evidence-sdlc | PreToolUse (Edit\|Write\|MultiEdit) | `FIX_TASK=1` (must be set for this gate to activate at all; when active, denies edits to test files/dirs) |
| `block-protected-branch-push.sh` | evidence-sdlc | PreToolUse (Bash, `git push *`) | None — no bypass; relies on real server-side branch protection as the actual control |
| `production-gate.sh` | evidence-sdlc | PreToolUse (Bash, `*deploy*`) | `RELEASE_APPROVAL` (allows deploy commands whose command line contains the whole word "prod"/"production"); uses stderr + `exit 2`, not `permissionDecision` |
| `audit-log.sh` | evidence-sdlc | PostToolUse (Edit\|Write\|MultiEdit, async) | None (never blocks; writes to `.claude/logs/agent-edits.tsv`) |
| `preflight.sh` | evidence-sdlc | SessionStart | None (advisory only; never sets `permissionDecision` even on failure) |
| `session-context.sh` | evidence-sdlc | SessionStart | None (advisory only; reads `CHANGE_TICKET` for display, not enforcement) |
