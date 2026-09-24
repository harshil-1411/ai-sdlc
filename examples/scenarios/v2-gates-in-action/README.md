# Scenario: a Tier 3 auth change, with each v2 gate firing

**Who this is for:** anyone who wants to see what the engine does. Every message
below is real output from `scripts/engine/hook.sh` run against these tool calls in a
scratch repo; only the paths and the session id will differ for you.

## The story

> "Add TOTP multi-factor verification to login." Tracker key `AUTH-7`.

Policy sets a **Tier 3 floor** on `**/auth/**`, so this change is Tier 3 whatever
anyone would prefer. `/evidence-sdlc:start AUTH-7 3 feature MFA login` does three
things. It runs `evidence change start AUTH-7 --tier 3 --kind feature`. It switches to
`feature/AUTH-7-mfa-login`. And it writes `intent.md`, `spec.md` and `plan.md` under
`intent/2026-09-24-mfa-login/`, each headed `Tracker: AUTH-7` and `Risk tier: 3`. The
plan's `## Files claimed` lists `src/auth/mfa.py` and `tests/auth/test_mfa.py`.

## (a) Editing before approval is denied

`Write src/auth/mfa.py`:

> Writing src/auth/mfa.py: the plan for AUTH-7 has not been approved. Ask a human to
> review intent/2026-09-24-mfa-login/plan.md and send
> `/evidence-sdlc:approve AUTH-7 69710aaf135c` (or run
> `evidence approve AUTH-7 69710aaf135c` in their own terminal). An agent cannot
> approve its own plan.

There's no route around it. All of these are denied as `self-approval`: running
`evidence approve AUTH-7` from Bash, writing an `Approved by: Dana` line into the plan,
`gh pr review --approve`, and posting an `/approve-plan` comment. The Bash denial
reads:

> Approving a plan (and changing a change's tier) is a human action. Ask the human to
> run `/evidence-sdlc:approve <KEY> <plan-sha>` in the Claude Code prompt, or
> `evidence approve AUTH-7 …` in their own terminal.

## (b) The human approves the exact plan

`evidence change status AUTH-7` shows `plan sha256: 69710aaf135c`. Dana reads the plan
and sends the chat message `/evidence-sdlc:approve AUTH-7 69710aaf135c`. The
UserPromptSubmit hook records it. The model can't author a user prompt, so it can't
fake one:

> The human approved the plan for AUTH-7 (intent/2026-09-24-mfa-login/plan.md, sha256
> 69710aaf135c) as dana@example.com. The approval is recorded in
> .evidence/changes/AUTH-7/approval.json and binds to this exact plan text; editing the
> plan voids it.

Now `Write src/auth/mfa.py` is allowed. The same write in `acceptEdits` mode would still
be denied, because Tier 3 means no auto-accept:

> …change AUTH-7 is Tier 3, which requires per-change human review, but this session is
> in 'acceptEdits' mode. Switch to the default permission mode for Tier 3 work.

## (c) An edit outside the claims is denied

The agent decides the profile page should show MFA status, and edits
`src/users/profile.py`:

> Writing src/users/profile.py: src/users/profile.py is not in the approved plan's
> "Files claimed" for AUTH-7. Add it to the plan (which voids the approval) and ask for
> re-approval, or leave the file alone.

## (d) A Bash write is judged like an Edit

`cat > src/auth/mfa.py <<'EOF' … EOF` is allowed, because the file is claimed. The same
form aimed at an unclaimed file gets the same rule, tagged with how the write was made:

> [via Bash: redirect] Writing src/auth/session_store.py: src/auth/session_store.py is
> not in the approved plan's "Files claimed" for AUTH-7. …

A write the engine can't inspect is denied even when the target is claimed.
`python3 -c "open('src/auth/mfa.py','w').write('x')"` gets:

> This command modifies files in a way the gates cannot inspect (python3 inline code
> that writes files). Use the Edit or Write tools for file changes so the plan, claims,
> test-protection and secret checks can run.

## (e) Push waits for the review agents

`git commit -m 'AUTH-7 add TOTP check'` is denied until the message ends with
`Agent-Session: sess-42`, the trailer the engine asks for. With it, the commit goes
through. Then `git push -u origin feature/AUTH-7-mfa-login` and `gh pr create` are
both denied:

> Pushing for change AUTH-7 (Tier 3) needs these review agents to have run on it
> first: verifier, security-reviewer, code-reviewer. Dispatch them, act on their
> findings, then retry. Runs are recorded automatically in the audit log.

The agent dispatches all three. PostToolUse records each `agent-completed`, and the
push goes through. `git push origin HEAD:main` never would: *"This push would update
main, which is protected. An agent has no route to a protected branch…"*

## (f) Giving itself a release approval is denied as control plane

With no `RELEASE_APPROVAL`, the production deploy is denied. The agent tries to add
`"env": {"RELEASE_APPROVAL": "REL-1"}` to `.claude/settings.json`:

> .claude/settings.json is part of the control plane (settings, policy, approvals,
> change state or audit log). An agent may not write it. A human edits it directly…

`echo '…' > .claude/settings.local.json` gets the same answer, prefixed
`[via Bash: redirect]`. `~/.claude/settings.json` is denied as configuration outside
the repository. So the deploy stays denied:

> `kubectl apply` names a production target (prod-eu). Production changes need a
> release authorization: a human starts the session with RELEASE_APPROVAL set to the
> approved release record (matching ^[A-Z][A-Z0-9]+-[0-9]+$). The agent cannot supply it.

## Afterwards

Every denial, allowed edit and agent run is in `.evidence/audit/sess-42.jsonl`, and
Dana's approval is in `approval.jsonl`. Both are hash-chained, and `evidence audit
verify` prints `OK` for each. `evidence metrics` counts the denials by rule, including
one self-approval attempt. Read next: [gates-reference](../../../docs/gates-reference.md) (every rule, in order),
[policy-reference](../../../docs/policy-reference.md) (floors, claims, required agents),
and [regulated-change-tier3](../regulated-change-tier3/README.md) (the same tier, from
the compliance side).
