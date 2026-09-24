# Spec: Make the v2 lifecycle work end to end in a signed deployment
Tracker: PILOT-57   From: dogfooding session 1e01f04e (2026-09-24); no intent.md (Tier 2)
Risk tier: 2 — fixes to the gate engine's lifecycle, commit gate and integrity monitor. These are trust-boundary code, but none of the policy tier floors apply (`scripts/engine/` matches no floor glob). The human set Tier 2 on 2026-09-24, knowing this is the human-only check itself.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Background: what dogfooding found
The first real v2 session on this repo (managed settings deployed, signing key live in hooks, hidden from the sandbox) could not complete one change. Every earlier v2 commit was made from a session running v1 hooks, so none of these defects was ever exercised.

| # | Defect | Observed | Code |
| --- | --- | --- | --- |
| D1 | Human-only CLI actions fail in a real terminal | `evidence change clear-violations` in the maintainer's own macOS terminal: "there is no terminal to confirm on". The maintainer confirmed `open("/dev/tty","r+")` raises `io.UnsupportedOperation: File or stream is not seekable` (a subclass of OSError), and `open("/dev/tty","r+b",buffering=0)` works | `lifecycle.py:27-33` |
| D2 | Agent commits are impossible on an active change | `git add <audit log> …` then `git commit` is denied "must be committed with it, up to date". Each tool call appends to the session audit log, so it is always unstaged-modified at commit time. Chaining `git add … && git commit` is denied too, because the check runs before the command | `evidence_policy.py:393-407` |
| D3 | Chaining `git switch -c …` with `evidence change start …` makes the monitor delete the new state.json and open a violation | observed on PILOT-54 | `integrity.py:101-124` (`cli_writes` returns ∅ when any non-CLI program is present) |
| D4 | `git reset` (unstaging) then `git switch` flagged an unchanged, untracked `plan/PILOT-54.md` as a plan write and opened a violation on PILOT-57 | observed | `integrity.py:67-98`: an untracked directory is collapsed to one entry (`plan`) whose key did not exist when the file was staged (`plan/PILOT-54.md`) |
| D5 | An agent cannot start a Tier 2+ change in a signed deployment | `evidence change start PILOT-57 --tier 2` from the agent: "no signing key (UNSIGNED MODE)" | `lifecycle.py:193-198` checks the key in the sandboxed shell, where the managed settings hide it by design |
| D6 | Change state written by an agent in a signed deployment is unsigned, and the hook then rejects it | PILOT-54's state.json was written by the agent's CLI (no key). `evidence_policy.py:161-164` denies every edit on a change whose state fails `signing.verify` | `state.py:249-257`, `evidence_policy.py:161` |
| D7 | Approvals and cleared violations written from a human terminal without the key are unsigned, and a signed session rejects them | follows from `signing.sign` being a no-op without the key (`signing.py:37-40`) and `approval` / `violations` verification (`state.py:278`, `:409`) | `lifecycle.py` human actions |

## Requirements
| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-SLF-01 | The human-terminal check opens the controlling terminal in a way that works on a real TTY, and still refuses inside Claude Code or with no TTY | D1 | A pseudo-terminal slave (`os.openpty`) passed to the check can be written to and read a confirmation line from. With `CLAUDECODE` set it still raises HumanOnly |
| REQ-SLF-02 | An agent commit on an active change is allowed when the session audit log's staged content is an exact byte prefix of the working file (only appended since staging, at most 2 entries). It is denied when the log is unstaged or untracked, or when the staged content is not a prefix (altered or truncated). state.json, approval.json and approval-KEY.jsonl keep the exact up-to-date rule | D2 | Engine test: stage log → append line → commit judged allow. Stage log → rewrite the first line → deny. Log never staged → deny. state.json modified after staging → deny |
| REQ-SLF-03 | The integrity monitor records untracked directories per file, so a status change with no content change (staged ↔ untracked) is not reported as a write. A file whose content really changes inside an untracked directory is still judged | D4 | Engine test: new file staged → snapshot → `git reset` → check reports no violation. Snapshot → write a new file into an untracked, claimed-gated directory → check reports it |
| REQ-SLF-04 | When an agent runs `evidence change start` or `evidence change advance` as the whole Bash command (optionally after `cd`), the PreToolUse hook performs the operation itself, with the engine's own code and key, and answers the call with the CLI's output. The resulting state.json is signed when a key is deployed. The Tier cap for unsigned mode is applied there, where the engine knows whether signing is on. If the same subcommands are chained with other programs, the call is denied with "run it as its own command" and nothing is written | D3, D5, D6 | Engine tests with a key: start (Tier 2) → state.json exists and `signing.verify` is True. Advance → signed. Chained with `git switch` → denied, no state. Without a key: Tier 2 start → denied with the unsigned-mode reason, Tier 1 → allowed. The agent's own `./evidence` script named in the command is never executed by the hook |
| REQ-SLF-05 | Human-only CLI actions (`approve`, `change set-tier`, `change release`, `change clear-violations`) refuse to write when the repository already holds signed records but this terminal has no `EVIDENCE_SIGNING_KEY`. The message says how to supply the key for one command, or to use the prompt channel for approval | D7 | CLI test: repo with a signed state.json, no key, no CLAUDECODE → exit non-zero with the key message, before any TTY prompt, and nothing is written |
| REQ-SLF-07 | The session audit log cannot fork under concurrent tool calls: `audit_append` holds an exclusive lock while it reads the last hash and appends | Verifier finding (3 forks in session 1e01f04e's log from parallel subagents) | Engine test: 20 concurrent appends from separate processes → `audit_verify` reports no break and no fork |
| REQ-SLF-08 | `audit verify` reports a fork (an entry whose `prev` equals the previous entry's `prev`, both hash-correct and, with a key, validly signed) as a named warning, not a failure. A deleted, altered or reordered entry still fails. Nothing rewrites a log | Same; CI runs `evidence audit verify` on committed logs | Engine tests: synthetic fork → ok with a "fork" warning; middle entry deleted → fail; entry altered → fail; forked sibling with bad signature (key set) → fail |
| REQ-SLF-09 | Hook-performed lifecycle calls are narrowed: (a) only `change start <KEY> --tier N --kind K` and `change advance <KEY> <stage>`, with any other option refused, so the hook writes only `.evidence/changes/<KEY>/state.json`; (b) only when the resolved directory's repository is the one in `CLAUDE_PROJECT_DIR` (when set); (c) never for a read-only agent; (d) the written history entry carries `via: hook` and the agent session ID. The human `--plan` path check is case-insensitive | Final security review (2026-09-24): case-insensitive `.Claude/…` write (High, confirmed), symlink race (High), repo anchored to a movable cwd, read-only agents, attribution | Engine tests: `--plan`/`--quick`/`--files` via the hook → refused, nothing written; `.Claude/commands/x.md` via the human CLI → refused; `CLAUDE_PROJECT_DIR` pointing elsewhere → refused; `agent_type` security-reviewer → refused; history has `via: hook` and the session |
| REQ-SLF-06 | `docs/managed-settings.md` states that human terminal actions need the key in that terminal's environment, gives the one-shot export command, and says an agent's `evidence change start/advance` is performed by the hook | D5–D7 | Content check on the doc |

## Design
- **REQ-SLF-01** (`lifecycle.py`): `_human_tty(path="/dev/tty")` returns a small object with `write`, `flush` and `readline`. It is backed by a read handle `open(path, "r")` and a write handle `open(path, "w")`. Each is a non-updating text stream, so no seekability is required. The same object serves the four existing callers (`:263`, `:289`, `:358`) unchanged. The `path` parameter exists for the pty test only.
- **REQ-SLF-02** (`evidence_policy.py` commit check): for `.evidence/audit/<session>.jsonl` only, "up to date" becomes: the path is staged (or tracked), `git show :<path>` is a byte prefix of the working file, and the unstaged tail is at most `AUDIT_TAIL_MAX = 2` lines. Other evidence files keep the current rule. *Added at the step-5 checkpoint:* without the cap, a tracked log could stay unstaged across any number of commits. The engine appends one entry per completed tool call (`hook.py:113`), so the `git add` call leaves a tail of one.
- **REQ-SLF-03** (`integrity.py` `_dirty`): when a porcelain entry is a directory (collapsed untracked dir), emit one entry per file (`rel/path → hash`) instead of one directory hash. It uses the same walk and the same 2000-file cap per directory as today. `check()` then compares per-file keys, which match the staged form.
- **REQ-SLF-04** (`hook.py` PreToolUse Bash path, reusing `evidence_policy._is_evidence_cli` and `cmdparse.split_simple`): if the parsed command is only `cd …` glue plus one evidence CLI call whose args start `change start` or `change advance`, the hook calls `lifecycle.main(argv)` in-process. It does this with `cwd` set to the command's directory and stdout/stderr and SystemExit captured, and returns a deny decision whose reason begins `Done by the gate engine:` followed by the output. The Bash command itself never runs, so the agent's sandbox never writes state.json, and `integrity.cli_writes` is no longer needed for these subcommands. It stays for `approve --github-pr`. If those subcommands appear alongside any other program → deny "run `evidence change …` as its own command". `lifecycle.py:193-198` keeps its check. Inside the hook it now sees the real key, and a human terminal keeps today's behaviour. The hook never executes a file named by the agent; it imports the engine's own `lifecycle` module from the plugin root.
- **REQ-SLF-05** (`lifecycle.py`): `_require_key_if_signed(root)` runs before `_human_tty()` in the four human actions. Signed deployment is detected by any `.evidence/changes/*/state.json` or `approval.json`, or any `.evidence/violations/*`, carrying a `sig` field.
- Existing components reused: `cmdparse.split_simple`, `_is_evidence_cli`, `signing.sign/verify`, `state.save_state`. Nothing new is added beyond the small TTY wrapper class.

## Regulatory control impact
`.evidence/context/compliance.md` establishes no applicable framework for this repository (every row is `[ASK]`), so no control set is loaded.

| Framework | Control ID | Applies? | How it is satisfied | Evidence |
| --- | --- | --- | --- | --- |
| none established | — | N/A | compliance.md lists none; awaiting maintainer | `.evidence/context/compliance.md:36` |

These fixes do strengthen what the framework claims for other repos (SOC 2 CC8.1 change management in `governance/control-mapping.md`): signed approvals and state are actually producible in a signed deployment.

## Evidence impact
- New requirement rows REQ-SLF-01..09, proven by engine, lifecycle and content suites via `validation/results/*.xml`.
- REQ-SLF-09(b) as built is stricter than first written: when `CLAUDE_PROJECT_DIR` is unset, the hook performs nothing (fails closed).
- The final verification caught a race in the F3 recovery. Two first appends racing to create `.evidence/audit/` made the loser treat `FileExistsError` as a tampered log and move a healthy log aside (2 of 20 entries lost, 1 of 13 runs). Fixed: `_dir_fd` tolerates a concurrent mkdir, and recovery runs only when the log itself exists and is refused. The REQ-SLF-07 test now also checks child exit codes and that no log was moved aside. That stricter test then exposed a second first-creation race: one child in some runs got `FileNotFoundError` from `openat(O_CREAT)` inside the freshly created `.evidence/audit/` (macOS; root cause not established further). `open_append` now re-walks and retries up to 5 times on that error. Result: 20 of 20 runs pass, against 5 failures in 25 before.
- No existing REQ row is retired. REQ-V2A-01 (signed approvals) and REQ-V2S-01 (lifecycle) gain real-deployment coverage; their existing tests must still pass unchanged.
- PILOT-54's unsigned state.json cannot be repaired by this change. A human deletes `.evidence/changes/PILOT-54/` and restarts it after this merges.

## Diagrams
- Sequence (agent lifecycle call after the fix):

```mermaid
sequenceDiagram
  participant A as Agent (sandboxed Bash, no key)
  participant H as PreToolUse hook (has key)
  participant L as engine lifecycle.main
  participant S as .evidence/changes/KEY/state.json
  A->>H: Bash "evidence change start KEY --tier 2 --kind fix"
  H->>H: parse; only CLI + cd? else deny "run on its own"
  H->>L: main(["change","start",...]) in-process, cwd=repo
  L->>L: unsigned-mode tier cap (sees real key)
  L->>S: save_state (HMAC-signed)
  H-->>A: deny: "Done by the gate engine: Started KEY ..."
  Note over A,H: trust boundary: key never enters the sandbox
```

## Security design
- **Trust boundary:** the key stays in the hook process. The hook executes only its own `lifecycle` module, with argv taken from the parsed command. Stage values are already restricted by `AGENT_ADVANCE`, and `approved`/`released` are refused (`lifecycle.py:233-237`). Human-only subcommands remain denied by `evidence_policy.py:689`. The hook path covers only `change start` and `change advance`.
- **Security-review findings closed during implementation (2026-09-24):**
  - The hook is unsandboxed. `--intent/--spec/--plan` therefore must be a `.md` file inside the repository, outside `.git/`, `.evidence/`, `.claude/` and the control-plane globs (`lifecycle._artifact_path`).
  - `--quick` creates the plan with `O_EXCL|O_NOFOLLOW` and never overwrites.
  - The hook performs lifecycle calls only when the resolved working directory is the session's own repository.
  - `advance` refuses to re-sign state whose signature fails.
  - Each rule has an engine test ("REQ-SLF-04 security: …").
- **Forgery:** before this change, an agent in a signed deployment could not produce signed state at all. After it, the agent can get only what `lifecycle.main` would write for `start`/`advance`, which is the intended capability. It cannot choose the content.
- **Audit prefix rule (REQ-SLF-02):** an agent could stage an older prefix of its log to leave recent entries out of one commit. Those entries stay on disk (the monitor denies shrinking, `integrity.py:262-266`) and are included in the next commit. The final commit of a branch can omit a tail of up to a few entries. This is accepted and noted in docs. Before this change, commits were impossible, which is worse for evidence.
- Required review agents: verifier, security-reviewer (Tier 2 per state).

## UX
| State / concern | Behaviour |
| --- | --- |
| Error | Every refusal names the next action: the key export for D7, and "run it as its own command" for chained lifecycle calls |
| Success | The agent sees `Done by the gate engine: Started …` as a denial reason. Documented, so it is not mistaken for a failure |

Component reuse: N/A — no UI.

- **Fourth security pass (human chose to fix these in PILOT-57, within the approved claims):**
  - **N1:** every engine write goes through `state.write_file` / `state.open_append`. Directory handles are opened with `O_NOFOLLOW` from the repository root. Whole-file writes use a fresh `O_EXCL` temp file renamed into place. Appends refuse non-regular or multiply-linked files. This also closes the same hole in 2.0.0's hook writes (audit, violations, state, restore).
  - **N2:** in PostToolUse, an unreadable change state or an unjudgeable write is recorded (engine-error entry, branch-level violations), never swallowed.
  - **N3:** the unstaged audit tail may hold only this session's `tool` entries.
- **Fifth security pass (human decision: fix what PILOT-57 introduced, plus the trivial F2; defer the rest):**
  - **F3:** an audit log the engine cannot append to (hard-linked, read-only, not a file) is moved aside through the directory handle and kept. A fresh log starts with an `audit-log-replaced` entry, and an `audit-tamper` violation is recorded. If even that fails, PreToolUse denies every call.
  - **F5:** the tolerated unstaged tail must chain from the staged last hash, hash correctly, and verify.
  - **F2:** an exception inside `integrity.check` is recorded as an `integrity-check-error` violation.
- **Tracked for PILOT-58, not fixed here:**
  - **F1 (High, pre-existing in 2.0.0):** the monitor's removal of a created control-plane file follows symlinked directories, so an agent can have files outside the repository deleted.
  - **F4 (High, pre-existing):** a non-regular entry at a violations path makes violations unrecordable while the push gate reads none.
  - `git commit -- <paths>` / `--only` bypass the index-based commit checks (pre-existing).
  - The fork rule is only checked against the immediate predecessor (reachable only where flock failed).
  - Integrity snapshots in the shared temp directory are written without symlink checks.
  - **Possibly Critical, pre-existing in 2.0.0:** hooks run `git` unsandboxed, with the key in their environment, in `ctx.root`. A repo-level `core.fsmonitor` or hooks path under the agent's control would execute there.
  - Neither the integrity monitor nor audit_append-era snapshots are concurrency-safe.
  - Deletions inside untracked directories are not judged.

## Areas of concern
- The hook performs `change start/advance` before Claude Code's permission step. With the shipped managed settings, `evidence change …` is already allowed without a prompt. A deployment that prompts for it loses that prompt; only plan mode is honoured. Owner: maintainer. Options: accept, or act only in acceptEdits/auto modes.
- The "Done by the gate engine" result arrives as a PreToolUse *deny*. `updatedInput` (rewriting the command to `echo <result>`) would read better, but it makes the hook depend on that feature's semantics. Owner: maintainer. Revisit if agents misread the denial.
- Signed-deployment detection (REQ-SLF-05) is a heuristic: the first human action in a brand-new repo with no signed records will not be refused. Acceptable, because the hook's verification rejects the unsigned result anyway.

## Architecture decisions
| ADR | Created / Supersedes / Relies on | Status |
| --- | --- | --- |
| none recorded in `.evidence/decisions/` | Relies on the undocumented v2 decision "key held by hooks, hidden from sandbox" (HANDOFF.md "Decisions worth knowing") | — |

## Rejected alternatives
- **Post-hoc re-signing of agent-written state by the integrity monitor.** The agent controls what runs under the name `evidence` (e.g. `python3 ./evidence`), so the monitor would be signing arbitrary content.
- **Exposing the key to the sandbox, or raising `unsigned_max_tier`.** Either defeats the signing design.
- **Letting `git switch` through `cli_writes` next to the CLI.** A branch switch can change committed control-plane files. With REQ-SLF-04, lifecycle calls no longer go through `cli_writes`, so this is moot.
- **The engine auto-staging the audit log at commit time.** A hook mutating the index is surprising, and races with the commit.
