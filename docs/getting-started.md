# Getting started

A walkthrough for someone installing Evidence Chain for the first time and taking
one real piece of work from idea to a traceability row. It does not repeat the
architecture-level explanation in the main [README](../README.md) — read that
afterward for the whole picture. This is the path through it.

## 1. What this actually is

Evidence Chain is a set of Claude Code plugins — skills, hooks and agents — that turn
"an agent wrote this" into a committed, reviewable paper trail: what was asked for,
what was designed, what was built, what proved it, and who approved it. The skills
make the standards likely; a small set of hooks make the non-negotiable ones
deterministic (a hook can deny an edit or a commit outright). None of it makes
anything compliant on its own — every gate ends at a named human. Read
[DISCLAIMER.md](../DISCLAIMER.md) before you rely on any of it for a regulated
product.

## 2. Prerequisites

- Claude Code, with plugin marketplaces enabled.
- `git`.
- `jq` on your `PATH` — the gate hooks in `evidence-sdlc` and `evidence-quality`
  shell out to it. `evidence doctor` (step 8) checks this for you.
- Python 3 if you want to run `cli/evidence` — standard library only, nothing to
  `pip install`, no network access.

Nothing else. There is no server, no database, no account to create.

## 3. Install the two core plugins

From the README's [Install](../README.md#install) section, run these inside Claude
Code:

```
/plugin marketplace add <your-org>/evidence-chain
/plugin install evidence-discovery@evidence-chain
/plugin install evidence-sdlc@evidence-chain
```

That's the minimum to do everything in this guide. Read the hook scripts before you
install anything — they run on your machine with your permissions
(`plugins/evidence-discovery/scripts/`, `plugins/evidence-sdlc/scripts/`). See
[SECURITY.md](../SECURITY.md).

You will hit two gate names later in this guide — `gate-plan-exists` and
`require-issue-key` — that are worth knowing come from different plugins.
`gate-plan-exists` ships in `evidence-sdlc`, which you just installed.
`require-issue-key` actually ships in `evidence-quality`
(`plugins/evidence-quality/scripts/require-issue-key.sh`), not in the two plugins
above — install it when you get there:

```
/plugin install evidence-quality@evidence-chain
```

Add `evidence-compliance` and `evidence-integrations` later, only when you need
them — each is its own install, not a bundle.

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
  `.evidence/adapter.example.yml`'s field list — see step 8)
- `.evidence/context/compliance.md`

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

## 6. Produce spec.md and plan.md

**spec.md — check the tier first.** Per the Definition of Ready table in
`risk-tiering`: at **Tier 1, `spec.md` is not required** — the ticket plus a stated
problem and acceptance criterion is enough. At Tier 2 and Tier 3 it's required, and
at Tier 3 it needs the full regulatory control table with every control given a
verdict. If your work is Tier 1, you can skip straight to `plan.md` below — though
writing a short spec anyway is often worth it whenever there are real edge cases to
settle on paper (this is exactly what
[`examples/scenarios/new-feature-non-regulated`](../examples/scenarios/new-feature-non-regulated/README.md)
does).

If you do write one, `spec-and-design` has a hard precondition: it reads
`.evidence/context/stack.md` first and **stops** — no spec, no schema, no design —
if that file doesn't exist, or if it carries an unresolved `[ASK]` in an area the
change depends on. This is why step 4 comes before this step. It writes
`spec.md` from `plugins/evidence-sdlc/templates/spec.md`, next to your
`intent.md`, with requirement IDs (`REQ-<area>-<nn>`) each traceable back to a line
in `intent.md` — those IDs are what `cli/evidence` looks for in step 8.

**plan.md — required at every tier, no exception.** `codebase-grounded-planning`
has the same stack-profile precondition and the same stop. It runs in plan mode
first (read-only), dispatches the `codebase-cartographer` agent to find what
already exists in this area before proposing anything new, and only then writes
`plan.md` (or `plan/<TRACKER-KEY>.md` if more than one session might be planning
against this repo at once) from `plugins/evidence-sdlc/templates/plan.md`. Every
path under "Files that change" has to be real — a path you or the cartographer
actually verified exists, or a new path in a directory that already exists. Get
your own sign-off on it before implementation starts; the plan is what the next
gate checks for.

## 7. What the gates will do to you

These are hooks, not skills — they run deterministically, not on a model's
judgment call, and they can outright deny a tool call. From the README's
[gates table](../README.md#the-gates) and the two hooks.json files:

- **`gate-plan-exists`** (evidence-sdlc) denies your very first `Edit`/`Write` if
  there's no `plan.md` or `plan/<TRACKER-KEY>.md` on disk yet. This is what step 6
  is actually for — skip it and your first edit gets refused, not just warned
  about.
- **`protect-validated-paths`** (evidence-sdlc) denies an edit to a
  change-controlled path if there's no change ticket recorded for it.
- **`block-test-weakening`** (evidence-sdlc) denies editing the test that proves a
  bug fix while you're in a fix task — you have to fix the code.
- **`require-issue-key`** (evidence-quality, `require-issue-key.sh`) denies `git
  commit` if the message carries no tracker key. This is the one gate that isn't
  in the two plugins you installed in step 3 — install `evidence-quality` before
  you rely on it.
- **`block-protected-branch-push`** (evidence-sdlc) denies `git push` to
  `main`/`master`/`release*`/`hotfix/*` outright. There is no agent route to those
  branches — you open a PR and a human approves it.
- **`production-gate`** (evidence-sdlc) denies a deploy command past the point
  where release authorization would be needed.
- **`require-repo-profile`** (evidence-discovery) is advisory, not a deny — it
  makes every session start aware of whether `.evidence/context/` exists yet.

None of these ask permission first; they act on the tool call as it happens. If one
denies something, the denial message tells you what's missing (a plan, a ticket
key, an authorization) — that's the gate working, not a bug to route around.

## 8. Run the CLI against what you just produced

`cli/evidence` is the part of this framework that tests whether any of the above
actually produced something derivable, rather than just paperwork. No install step:

```
python3 cli/evidence doctor
```

`doctor` is preflight: `jq` on `PATH`, every `plugins/*/scripts/*.sh` readable,
every `hooks.json` parses and every script it references exists,
`.evidence/context/` present (and which profiles are missing), the count of
unresolved `[ASK]` items, and profile staleness (over ~6 months old). It exits
non-zero only on a critical failure.

```
python3 cli/evidence scan
```

Walks the repo (through `.evidence/adapter.yml` if you wrote one in step 4,
otherwise this framework's own default layout) and builds tracker key →
requirement → test → commit. A repo with no requirement IDs anywhere gets a plain
"nothing to trace" message.

```
python3 cli/evidence gaps
```

The honest question: `NO COVERAGE` (a requirement with no covering test),
`ORPHANED` (a test tracing to a requirement ID that doesn't exist), `UNTRACED` (a
commit with no tracker key), `UNPROVEN` (a requirement whose test's last recorded
result wasn't `PASS`). Coverage has to be structural — a requirement ID in a test's
name, tag, annotation or docstring, or an independently-verifiable
`validation/traceability.csv` row — not just the ID appearing somewhere near
something that looks like a test.

```
python3 cli/evidence export --format md --write
```

Writes `validation/traceability.md` (or `.csv`), appending rather than rewriting —
a requirement you haven't touched keeps its existing row.

**What a first-time honest result looks like:** if you've only done one
`intent.md` → `spec.md` → `plan.md` cycle, expect `gaps` to report real gaps — a
`NO COVERAGE` requirement if you haven't written the test yet, or an exit code of
`2` ("nothing to assess") if your one `spec.md`'s requirement IDs don't match
whatever pattern `.evidence/adapter.yml` (or the framework default,
`REQ-[A-Za-z0-9]+-[0-9]+`) expects. That's expected, not broken. The CLI's own
`cli/README.md` walks through exactly this kind of result against this
repository's own history — a real `NO COVERAGE` finding it refused to paper over
even though the underlying test genuinely exists and passes, because the
traceability row's claim couldn't be independently verified against the file it
named. Treat your first `gaps` run as a punch list, not a grade.

## 9. Where to go next

- The six worked scenarios in [`examples/scenarios/`](../examples/scenarios/) —
  start with
  [`new-feature-non-regulated`](../examples/scenarios/new-feature-non-regulated/README.md),
  the lightest path and closest to what you just did, then
  [`regulated-change-tier3`](../examples/scenarios/regulated-change-tier3/README.md)
  for the heaviest one and everything this guide's Tier 1 path skipped.
  `incident-bug-fix`, `schema-migration-regulated-table`,
  `third-party-integration` and `standalone-cli-audit` cover the other shapes of
  work. [`examples/README.md`](../examples/README.md) is the full index, including
  optional skills not installed by default.
- [`risk-tiering`](../plugins/evidence-sdlc/skills/risk-tiering/SKILL.md) for the
  full Definition of Ready / Definition of Done table by tier — this guide only
  walked the Tier 1 minimum.
- The main [README](../README.md) for the parts this guide deliberately skipped:
  how the plugins fit together, running parallel sessions safely, compliance
  without hardcoding a regulation, and the [rollout
  order](../README.md#rollout-order) for adopting this across a team rather than
  one person's one change.
