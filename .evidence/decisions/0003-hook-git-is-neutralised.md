# 0003. Harden engine git in hooks; accept and state the residual key exposure

Status: Proposed (revision 2, after the second security design review, 2026-09-24)
Date: 2026-09-24
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-58   Spec: intent/2026-09-24-integrity-monitor-hardening/spec.md
Supersedes: none
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- Hooks run unsandboxed with `EVIDENCE_SIGNING_KEY` in their environment. They run git (and `gh`) in the session's repository.
- The agent shapes that repository: config (includes, worktree config, `.git`-as-file), attributes (worktree, `info/attributes`, `core.attributesFile`), submodules, refs and the `GIT_*` environment.
- Many git features execute configured commands. Two security design reviews (2026-09-24) found that every fix at this level leaves another path:
  - newline-bearing config values;
  - included files reported under the including scope;
  - submodule config;
  - check-then-use races with a background process.

  So local hardening **reduces** the exposure but cannot close it while the key lives in the process that runs git.
- The first draft of this ADR also made the local push gate authoritative for commit contents. The second review showed that everything it would trust is agent-writable (base ref, pushed refs, merge commits). That decision moves to ADR-0004, server side.

## Decision
1. **Every engine git or `gh` process goes through one helper (`state.run_git` / `run_gh`):**
   - `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c core.pager=cat -c core.attributesFile=/dev/null -c diff.external= -c protocol.ext.allow=never -c submodule.recurse=false`;
   - `--ignore-submodules=all` on status and diff;
   - `--no-ext-diff --no-textconv` on diff, log and show;
   - `GIT_ATTR_SOURCE` set to the empty tree computed with `git hash-object -t tree /dev/null`, when supported;
   - an environment with every `GIT_*` variable **and `EVIDENCE_SIGNING_KEY`** removed;
   - `gh` calls pass `--repo <pinned github_repo>`.
2. **Config check.** Before git calls other than `rev-parse`, the hook reads config with `git config --list -z --show-scope --show-origin --includes`, run with the same neutralisations.
   - It refuses any key in the command-executing deny set at **any scope except `command`**. `credential.*` is allowed at global or system scope only, since the engine's git calls make no network use.
   - It refuses if an allow-listed key's value contains a newline or carriage return.
   - An exact key=value in the org `git_allowed_config` passes (the git-lfs defaults).
3. **Git failure fails closed.** If the pre-snapshot saw a repository and git now fails, the monitor records `git-unavailable` and still restores the control plane and checks audit prefixes through the filesystem. A `.git` entry at or above the root with git failing is a deny.
4. **Residual risk, accepted and stated.** The key can be exposed to the agent in two ways:
   - **A race.** A command the agent started can change repository config or attributes between the hook's check and its git call, so git runs a command. Removing the key from child environments means that command doesn't inherit it.
   - **Reading the environment, with no git involved.** Any same-user process that can inspect the hook process while any hook runs can read its environment, where the OS allows same-user inspection (`/proc/<pid>/environ`, `ps eww`). The regex denial of `printenv` and similar commands doesn't stop a script file doing this. Whether the OS sandbox blocks it depends on the platform [NEEDS VERIFICATION: Seatbelt / bubblewrap process-inspection rules].

   **With the key, an agent can forge every signed local record** (approvals, state, audit entries). CI does **not** mitigate that for records: the key is symmetric and shared with CI. The merge decision is protected independently, by ADR-0004: approval comes from a GitHub code-owner review, not from the signed `approval.json` alone. The structural fix is a separate signer that never runs git or exposes the key in its environment (PILOT-61).

## Consequences
- Easier: one audited place where the engine starts external programs. Most repository-controlled execution paths are closed.
- Harder:
  - repositories with local custom filters or diff drivers are refused until the org allow-lists exact values;
  - submodule changes are not seen by the monitor, which is acceptable because they are recorded as gitlinks.
- Constrained: new engine subprocess calls must use the helpers. An AST test enforces it (REQ-IMH-22).
- Review trigger: reopen when PILOT-61 (key isolation) lands. This ADR's residual-risk section should then be withdrawn.

## Alternatives
| Option | Why it lost |
| --- | --- |
| Parse `.git/config` by hand | Disagrees with git on quoting, includes and worktree config, so it's a bypass |
| Allow-list key names | Values are what execute |
| Make the local push gate authoritative for commit contents | Base refs, pushed refs and merge commits are agent-controlled locally (second review F6–F9); moved server side, ADR-0004 |
| Isolate the key now | The right end state, but an architectural change (signer process or keychain); PILOT-61 |
