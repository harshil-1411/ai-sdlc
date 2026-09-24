# 0003. Neutralise repository-controlled execution in engine git; validate commits at push

Status: Proposed
Date: 2026-09-24
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-58   Spec: intent/2026-09-24-integrity-monitor-hardening/spec.md
Supersedes: none
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- Hooks run unsandboxed with `EVIDENCE_SIGNING_KEY` in their environment. They run `git status`, `git diff --cached`, `git show` and more in the session's repository, and the agent can shape that repository:
  - its config (through `.git` files, include paths, worktree config);
  - its `.gitattributes`;
  - its `GIT_*` environment.
- Several git features execute configured commands: fsmonitor, hooks, clean, smudge and process filters, `diff.<drv>.command`, textconv, external diff, pager, ssh, askpass and credential helpers. Any of them would run code with the key.
- The commit gate (`evidence_policy._check_commit`) inspects the index at PreToolUse time. Index changes in the same command, `GIT_INDEX_FILE`, `-p`, pathspecs, and history-writing commands other than `commit` (merge, cherry-pick, rebase, `commit-tree` + `update-ref`) all bypass it. The push gate re-checks only violations and review agents.

## Decision
1. **Every engine git process goes through one helper, `state.run_git`:**
   - `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c core.pager=cat -c diff.external= -c protocol.ext.allow=never`;
   - `--no-ext-diff --no-textconv` on `diff`, `log` and `show`;
   - `GIT_ATTR_SOURCE` set to the empty tree where git supports it (≥ 2.40, detected at runtime), so working-tree attributes can't pick drivers;
   - an environment with every `GIT_*` variable removed, except the ones the helper sets.
2. **Before any git call other than `rev-parse`, the hook asks git itself for the configuration.**
   - The call is `git config --list --show-scope --includes`, run with the neutralisations above. Listing configuration runs nothing.
   - The hook refuses (fail closed) if any **local or worktree-scope** key matches the command-executing deny set, unless the exact `key=value` pair is in `git_allowed_config` (org policy). The defaults cover the three git-lfs filter values.
   - The git directory is resolved with `rev-parse --git-dir --git-common-dir`, never assumed to be `.git/`.
   - A refusal inside PostToolUse records a `git-config-refused` violation. The monitor's non-git checks still run.
3. **The push gate validates what was actually committed.** For each commit in `merge-base(base, HEAD)..HEAD`, it checks the committed tree:
   - paths against the plan's claims;
   - the change's evidence files present;
   - a secret scan of the blobs added.

   This covers plumbing, merges, cherry-picks and index tricks. The PreToolUse commit check stays as early feedback, and also denies pathspec, `--only`, `--include`, `-p`, `--interactive` and `--pathspec-from-file` commits. `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY` and `GIT_ALTERNATE_OBJECT_DIRECTORIES` join the environment spoof list.

## Consequences
- Easier: one audited place where the engine starts git. The commit guarantees hold however the history was written.
- Harder:
  - repositories with local custom filters or diff drivers are refused until the org allow-lists the exact values;
  - push checks take longer on long branches (bounded by the range).
- Constrained: new engine git calls must use `run_git`. A test asserts no other `subprocess` git call exists in the engine.
- Cost to reverse: low per piece; each rule is local.
- Review trigger: reopen if git adds a new command-executing config family, or if org allow-lists grow large enough to suggest a per-repo allow file.

## Alternatives
| Option | Why it lost |
| --- | --- |
| Parse `.git/config` by hand | Disagrees with git on quoting, includes, worktree config and `.git`-as-file, so it's a bypass |
| Allow-list key names (`filter.lfs.*`) | Values are what execute; `filter.lfs.clean = sh -c …` would pass |
| Only strengthen the PreToolUse commit check | It can't see index changes made later in the same command, or non-`commit` history writers |
| Run engine git in a sandbox without the key | Hooks need the key in-process; it's a larger architectural change, a candidate for a later ADR |
