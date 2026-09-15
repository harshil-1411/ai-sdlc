# Repository profile — toolchain and connectivity

Repo: evidence-chain   Established: 2026-09-10

Context: this repository is the Evidence Chain framework itself (a Claude Code plugin
marketplace), not a product repository being onboarded. Its own delivery toolchain is
therefore mostly undetermined — there is no tracker, CI, or test-management tool wired
up to *this* repo yet. Rows below record what was found, not what a consuming repo
would have.

| Tool | Used for | Connectivity class | Endpoint / command | Credential source | Scope | Access owner | If unreachable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| git | Version control, local commits | CLI | `git` (2.46.0, on PATH, `/opt/homebrew/bin/git`) | none needed (local repo) | n/a | [ASK] | Manual — no automation depends on it beyond local commits |
| GitHub (source hosting) | Would host the canonical `evidence-chain` repo and PRs | CLI | `gh` (2.100.0, on PATH) | keyring-stored OAuth token, account `harshil-1411` | scopes: `gist`, `read:org`, `repo`, `workflow` — **write-capable** | [ASK] — see finding below | Manual (no `gh` calls attempted this session; repo has no remote configured — `git remote -v` is empty) |
| Claude Code plugin marketplace | Distribution of this repo's own plugins | Manual / built-in | `/plugin marketplace add`, `/plugin install` | Claude Code session auth | n/a | [ASK] | Manual — this is the mechanism itself, not a dependency of it |
| Chrome browser automation | Exploration, UI reproduction (per `docs/third-party-tooling.md` "Recommended") | MCP-official | `mcp__claude-in-chrome__*` tools, available this session | Chrome extension, user's own browser session | read/interact with pages the user has open | user (session-local) | Manual — fall back to asking the human to check the browser |
| Issue tracker | None found | Manual | — | — | — | [ASK] | Everything issue-related (traceability IDs, intent capture linking) is manual until a tracker is chosen |
| Test management system | None found | Manual | — | — | — | [ASK] | `testrail-authoring` cannot run until a tool and its field schema are named |
| CI system | None configured (see `.evidence/context/deployment.md`) | Manual | — | — | — | [ASK] | `continuous-testing` design has nothing to attach to yet |
| Support desk | None found | Manual | — | — | — | n/a | Not applicable — this repo has no end users filing tickets |

## Write-path decisions

| Tool | Agent may write? | Approved by | Date | Constraints |
| --- | --- | --- | --- | --- |
| GitHub (`gh` CLI) | **Not yet decided** | — | — | Token is write-capable (`repo`, `workflow` scopes) but authenticated as `harshil-1411`, an account not yet confirmed as belonging to this session's user (`suparn.bector@msbdocs.com`, per session identity). Do not use `gh` for any write action (push, PR, issue, workflow dispatch) until ownership of this credential is confirmed. |
| git (local commits) | Yes, for local commits only | implicit — standard dev workflow | 2026-09-10 | No remote configured; nothing pushed anywhere by writing locally |

## Community MCP servers in use

| Server | Repo | Licence | Reviewed by | Date | Scope of credential | Read-only? |
| --- | --- | --- | --- | --- | --- | --- |
| — none configured | — | — | — | — | — | — |

## Open questions — [ASK]

1. **Credential ownership mismatch (security-relevant):** `gh auth status` shows this
   machine's GitHub CLI is authenticated as account `harshil-1411` with write scopes
   (`repo`, `workflow`), but the session's identified user is
   `suparn.bector@msbdocs.com`. Per `docs/toolchain-connectivity.md`, source-host write
   access should be scoped to the acting person's own permissions. Confirm whether this
   is (a) a shared/service account intentionally used on this machine, (b) a stale
   personal login from a previous user of this machine, or (c) unexpected. Until
   answered, no write action via `gh` should be taken from this repo. — awaiting: user
2. **No remote configured.** `git remote -v` is empty — this repo has never been pushed
   anywhere. Confirm the intended canonical host (GitHub org/repo name) before any
   `git push` is attempted; `managed-settings.json`'s `strictKnownMarketplaces` already
   references `<your-org>/evidence-chain` as a placeholder. — awaiting: maintainer
3. **No issue tracker, test management tool, or CI system chosen** for evidence-chain's
   own repo. `evidence-quality:traceability-ids`, `testrail-authoring`, and
   `continuous-testing` cannot be applied to changes made *to this framework* until
   these are named. (This does not block consuming repositories, which run their own
   discovery.) — awaiting: maintainer
