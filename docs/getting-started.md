# Getting started

This walkthrough is for someone installing Evidence Chain for the first time. It takes
one real piece of work from an idea to a traceability row. It doesn't repeat the
explanations in [concepts.md](concepts.md); read that afterwards for the whole
picture.

## 1. What this actually is

Evidence Chain is a set of Claude Code plugins: skills, agents, slash commands and one
gate engine. Together they turn "an agent wrote this" into a committed, reviewable
paper trail of what was asked for, what was designed, what was built, what proved it,
and who approved it.

The skills make the standards likely. The engine makes the non-negotiable ones
deterministic: it's a Python hook that can deny an edit, a Bash command, a commit or a
push outright. None of it makes anything compliant on its own, and every gate ends at
a named human. Read [DISCLAIMER.md](../DISCLAIMER.md) before relying on any of it for a
regulated product.

## 2. Prerequisites

- Claude Code, with plugin marketplaces enabled.
- `git`.
- **Python 3.8+** on your `PATH`. The gate engine and the `evidence` CLI need it, and
  use only the standard library, so there's nothing to `pip install`. If `python3` is
  missing, the engine **fails closed**: every file change and command is denied, and
  the session start says `EVIDENCE CHAIN GATES NOT RUNNING`. `jq` is no longer needed.

Nothing else: no server, no database, no account.

## 3. Install all five plugins

Add the marketplace. From a local clone, which works today:

```
/plugin marketplace add /path/to/evidence-chain
```

(or `claude plugin marketplace add /path/to/evidence-chain` from your shell). Once
the owner has pushed the repository to a git remote, `/plugin marketplace add
<owner>/evidence-chain` works too.

Then install all five. They declare dependencies on each other, and the commit,
test-protection and review-agent rules all live in `evidence-sdlc`'s engine, so a
partial install gives you a partial picture:

```
/plugin install evidence-discovery@evidence-chain
/plugin install evidence-sdlc@evidence-chain
/plugin install evidence-quality@evidence-chain
/plugin install evidence-compliance@evidence-chain
/plugin install evidence-integrations@evidence-chain
```

Read the engine before you install it (`plugins/evidence-sdlc/scripts/engine/`). It
runs on your machine with your permissions. See [SECURITY.md](../SECURITY.md).

**Check it's live.** Start a new session and ask *"what did the Evidence Chain
session-start context say?"* It must quote `Evidence Chain gates live (engine 2.0.0; …)`.
For a stronger test, on a branch with no tracker key, ask Claude to create
`src/x.py`. It must be denied. If either check fails, see
[managed-settings.md](managed-settings.md#the-canary).

## 4. Run discovery on a real repository

Open the repository you actually want to onboard (not this one) and ask a stack
question — "what stack does this repo use" works, so does just starting to plan
something. `stack-discovery` does not wait to be asked to run: if
`.evidence/context/` is missing or stale, it runs the survey itself and answers
from the result.

What it actually does, in order (from
`plugins/evidence-discovery/skills/stack-discovery/SKILL.md`): reads manifests and
lockfiles first (the lockfile is truth, the manifest is intent), then runtime pins,
entry points, the data layer, build/test tooling, deployment config, observability,
and version-control conventions. It never trusts your README or CLAUDE.md for a
stack fact — if the docs and the code disagree, the code wins, and it says so.

It writes two files, and commits them:

- `.evidence/context/stack.md`
- `.evidence/context/deployment.md`

Run `toolchain-discovery` and `compliance-discovery` the same way (ask "what's our
tracker", "are we connected to CI", "do any regulations apply to this product" — or
just let them fire when a workflow needs them). They add:

- `.evidence/context/toolchain.md`
- `.evidence/adapter.yml` (toolchain-discovery writes this from
  `.evidence/adapter.example.yml`'s field list — see step 9)
- `.evidence/context/compliance.md`

Then run `test-strategy-discovery` (ask "what's our test strategy" or "what testing
should we be doing"). It reads the repository first and asks the team one batch of
questions about what the repository can't answer: test types in scope, performance
and accessibility targets, environments, browsers, and who owns UAT and the go/no-go.
It adds:

- `.evidence/context/test-strategy.md`

Every line in these files carries a confidence marker: `[confirmed]` (read from a
file, cited), `[inferred]` (strong evidence, not declarative), or `[ASK]` (could not
be established — a question is written out, waiting for a human).

**What an `[ASK]` actually looks like** — a real line from a profile, not a
paraphrase:

```
- Test framework: [ASK] — a `tests/` directory exists with two spec files, but no
  test runner config was found anywhere in the manifest or CI. What runs these?
```

**What to do about one:** answer it. `[ASK]` isn't a TODO you can leave — any
downstream skill that depends on that area treats an unresolved `[ASK]` as a
blocker, not a detail. `spec-and-design` and `codebase-grounded-planning` both
explicitly refuse to proceed while an `[ASK]` in a relevant area is open. At the
end of a discovery run you'll be shown the `[ASK]` list as numbered questions,
most consequential first — answer them, and whichever skill wrote the profile
records who answered and updates the line to `[confirmed]`.

## 5. Capture your first intent.md

Pick one real, small piece of work — a bug, a small feature, whatever you'd
normally open a ticket for. Describe it to Claude in plain language; you do not
need to say the word "intent." `intent-capture` fires on anyone starting to
describe work in prose, not just engineers.

It interviews you like a business analyst, not a form. It needs an answer — or an
explicit "unknown" — for each of:

- What can't be done today, and who's affected?
- Does this touch a **regulated record** (anything a customer would cite in an
  audit — a signed/approved record, an audit trail, a consent record)?
- Does it change anything your compliance evidence or a customer's own validation
  asserts? (Read `.evidence/context/compliance.md` for what applies — if you ran
  step 4 honestly, this is answerable.)
- What does "better" look like, measurably?
- What's explicitly out of scope?
- Which data classes does this touch?

It will not design a solution for you at this stage — no API shapes, no table
names — and it will not estimate size. If you propose a solution anyway, it gets
recorded under "Proposed outcome" as *your* proposal, kept separate from the
problem statement.

The result is written to `intent/<yyyy-mm-dd>-<slug>/intent.md` from
`plugins/evidence-sdlc/templates/intent.md`, with every heading filled — "Unknown —
needs <role>" rather than a deleted section. Review it, correct anything it
misread, and commit it. Done means it's in git history with your name on it and
your product owner could accept or reject it without another meeting.

State the risk tier right after, in one line, per `risk-tiering`
(`plugins/evidence-sdlc/skills/risk-tiering/SKILL.md`) — e.g. *"Tier 1 — routine UI
fix, no regulated record, existing auth model reused."* Tier 3 is anything touching
the audit trail, signatures, record integrity, auth, tenant isolation, key
material, or residency; Tier 2 is a non-regulated production path; Tier 1 is
everything else. When in doubt, tier up.

## 6. Start the change, and produce spec and plan

**Start the change.** Every source edit needs an *active change*: a branch named with
the tracker key, plus lifecycle state. The easy way:

```
/evidence-sdlc:start PAY-142 1 feature CSV export for team admins
```

This runs `evidence change start PAY-142 --tier 1 --kind feature` (it writes
`.evidence/changes/PAY-142/state.json`) and switches to a branch such as
`feature/PAY-142-csv-export`. Then it produces what the tier requires:

| Tier | Needs before any source edit |
| --- | --- |
| 1 | plan |
| 2 | spec + plan |
| 3 | intent + spec + plan |

The engine finds the artifacts in two places: `plan/<KEY>.md`, or
`intent/<date>-<slug>/{intent,spec,plan}.md` whose header carries `Tracker: <KEY>`.
Policy sets **tier floors**. If the change touches auth, crypto, signing, audit or
migrations, a Tier 1 or 2 change is denied on those paths until a human raises the
tier (`evidence change set-tier KEY 3`, in their own terminal).

**spec.md.** It isn't required at Tier 1, but it's often worth writing a short one
anyway (as in
[new-feature-non-regulated](../examples/scenarios/new-feature-non-regulated/README.md)).
`spec-and-design` reads `.evidence/context/stack.md` first and **stops** if that file
is missing or has an unresolved `[ASK]` in an area this change depends on. That's why
step 4 comes first. Requirement IDs (`REQ-<area>-<nn>`) trace back to `intent.md`, and
they are what the CLI looks for in step 9.

**The plan is required at every tier.** `codebase-grounded-planning` runs read-only
first, and dispatches `codebase-cartographer` to find what already exists. Then it
writes the plan from `plugins/evidence-sdlc/templates/plan.md`. The engine enforces
two sections:

- `## Files claimed`: the exact paths or globs this change may edit. Once the plan is
  approved, any edit outside them is denied.
- `## Order of work`: the ordered steps. Tier 2 and 3 plans should include a
  CHECKPOINT step.

A plan without both sections, or one still holding template placeholders, is a stub,
and a stub can't be approved.

## 7. Approve the plan (you, not the agent)

Run `/evidence-sdlc:status` (or `evidence change status PAY-142`). It prints the plan
path and its hash:

```
plan sha256: 69710aaf135c  (a human approves with: evidence approve PAY-142 69710aaf135c)
```

Read the plan. If it's right, send this **as a chat message**:

```
/evidence-sdlc:approve PAY-142 69710aaf135c
```

A `UserPromptSubmit` hook records `.evidence/changes/PAY-142/approval.json`, with your
`git user.email` as approver. That record is bound to that exact plan text. The sha
prefix is required: without it, or with a stale one, the hook records nothing and
replies with the hash to use.

The model can't author a user prompt, so it can't approve its own plan. The engine
also denies it running `evidence approve` itself, and denies writing an
`Approved by:` line into a plan, spec or intent, because approval lives only in
`approval.json`. If the plan changes afterwards, the approval stops applying, and you
re-read and re-approve the new hash. Two other channels exist:
`evidence approve PAY-142` in your own terminal (you type the hash prefix), and
`evidence approve PAY-142 --github-pr N` for an approval given on GitHub (see
[policy-reference.md](policy-reference.md#approval)).

## 8. What the gates will do to you

The engine runs on every tool call and acts without asking. Every denial explains
what's missing. That is the gate working, not a bug to route around. The ones you'll
meet first:

- **No approved change → no source edit.** That covers Edit and Write, and Bash writes
  like `cat > file`, `sed -i` and `cp`, which are judged exactly like an Edit. Docs,
  `intent/`, `plan/` and `.evidence/context/` are ungated.
- **Outside the claims → denied.** Add the file to the plan, which voids the
  approval, and get it re-approved.
- **Commits** need the key in the **message** (the branch alone isn't enough), and the
  last line must be the trailer the session-start context gives you:

  ```
  PAY-142 Add CSV export endpoint

  Agent-Session: 3b1f…
  ```
- **Push and PR** wait until the tier's review agents have run. `verifier` is needed at
  every tier, `security-reviewer` from Tier 2, and `code-reviewer` at Tier 3. Their
  runs are recorded automatically. Pushes to `main` or any protected ref, and
  `gh pr merge`, are always denied: a human merges.
- **Bug fixes.** Start with `--kind fix`, commit the failing test, then run
  `evidence change advance KEY failing-test`. After that, existing tests can't be
  edited ([incident-bug-fix](../examples/scenarios/incident-bug-fix/README.md)).
- **Human-only switches.** `CHANGE_TICKET` (migrations, CI, infra and the like),
  `RELEASE_APPROVAL` (production deploys) and `EVIDENCE_ACTIVE_CHANGE` are set by the
  person who starts the session. The agent can't set them, because settings files are
  control plane.

Two things advise and never deny. The session-start context says whether
`.evidence/context/` exists and how many `[ASK]`s are open. The sensor notes an
unfilled "Areas of concern" or "Files claimed" right after you write it. Full detail
is in [gates-reference.md](gates-reference.md), and
[v2-gates-in-action](../examples/scenarios/v2-gates-in-action/README.md) shows each
denial in context.

## 9. Run the CLI against what you produced

`evidence` is on `PATH` inside sessions. Outside a session, run
`python3 cli/evidence …` from a clone. These commands check whether the steps above
actually produced something you can trace, rather than just paperwork:

```
evidence doctor    # preflight: python3, a live gate-engine canary, hooks.json sanity, profiles, [ASK] count, control-set owners
evidence scan      # tracker key → requirement → test → result → commit
evidence gaps      # NO COVERAGE, FAILED, SELF-ASSERTED, UNPROVEN, UNVERIFIED-RESULT, ORPHANED, UNTRACED, …
evidence export --format md --write   # merge-write validation/traceability.md, never overwriting a filled cell
evidence audit verify                 # the session's hash-chained audit log is intact
```

Coverage has to be *structural*: the requirement ID has to appear in a test's name,
tag, annotation or docstring. A requirement is *proven* only by an ingested,
machine-readable passing result, such as JUnit XML or `--results`. A hand-typed `PASS`
never counts.

**What a first honest result looks like.** After one cycle, expect real gaps: `NO
COVERAGE` if the test isn't written yet, or exit code `2` ("nothing to assess") if
your requirement IDs don't match the configured pattern. That's expected, not broken.
Treat your first `gaps` run as a punch list, not a grade. See
[cli/README.md](../cli/README.md) for every category and exit code.

## 10. Where to go next

- The scenarios in [examples/scenarios/](../examples/scenarios/). Start with
  [new-feature-non-regulated](../examples/scenarios/new-feature-non-regulated/README.md),
  then [v2-gates-in-action](../examples/scenarios/v2-gates-in-action/README.md) and
  [regulated-change-tier3](../examples/scenarios/regulated-change-tier3/README.md).
- [`risk-tiering`](../plugins/evidence-sdlc/skills/risk-tiering/SKILL.md) for the full
  Definition of Ready and Done by tier.
- [concepts.md](concepts.md): parallel sessions, compliance, traceability and rollout
  order.
- [managed-settings.md](managed-settings.md) when you roll this out beyond one machine.
