---
name: codebase-grounded-planning
description: Build an implementation plan.md that is grounded in what the repository actually contains — real files, real existing APIs, real test locations — instead of a plausible-sounding plan. Use this at the start of every implementation session, whenever someone says "plan this", "how would we build this", "break this down", or asks for tasks, subtasks, or a work breakdown, and whenever a session is about to start editing code without an approved plan on disk.
---

# Codebase-grounded planning (Stage 3: Build)

## Precondition — stop if there is no stack profile

Read `.evidence/context/stack.md` before anything else. If it does not exist,
STOP. Do not produce a spec, a design, a schema, or a plan. Say that discovery
has not run and that designing against unverified stack facts is how confidently
wrong designs get built. Run stack-discovery, then resume.
This is not a warning to note and move past. It is a stop.

If the profile exists but carries an unresolved [ASK] in an area this change
depends on, that is also a stop — ask the human.

The single biggest failure mode of AI-assisted development here is a beautiful
plan that assumes an architecture we don't have. This skill exists to stop that.

## Concurrent sessions

Before planning, check for other active work: other worktrees, other `plan/` files,
and open branches touching the same paths. If another plan claims a file this plan
needs, STOP and say so — silent concurrent edits to one module is how two correct
changes produce one broken merge.

Changes that touch the same regulated path must not run concurrently. Sequence them
and say why.

Use `plan/<TRACKER-KEY>.md` (not bare `plan.md`) whenever more than one session might
be planning against this repository at once — it is what lets `gate-plan-exists`
tell one session's plan apart from another's, and lets a concurrent session see what
is already claimed via the plan's own "Files claimed" section (see
`templates/plan.md`).

## Sequence — do not reorder

1. **Start in plan mode.** You may read, grep and run read-only commands. You may
   not edit.
2. **Survey before proposing.** Dispatch the `codebase-cartographer` agent with the
   `spec.md` and ask it for: the modules that already own this concern, the existing
   API endpoints that already return the data needed, the existing test files that
   cover the area, the migrations that touch the same tables, and anything that looks
   like a near-duplicate of what's being asked for.
3. **Name real files.** Every line in the plan's "Files that change" section must be
   a path that exists, or a new path in a directory that exists. If you catch
   yourself writing a path you have not verified, stop and verify it.
4. **Reuse before adding.** If the cartographer found an existing endpoint or
   component that covers 80% of the need, the plan extends it. Adding a parallel
   implementation requires a written justification in the plan.
5. **Order the work** so that each step is independently verifiable, and mark which
   steps are independent (those can go to parallel sessions or worktrees).
6. **State the proof.** Apply the `test-strategy` skill. Every requirement ID from
   `spec.md` gets a row naming its layer, whether it is automated, its test case ID and
   its automated test. `REQ-...` with no named test is an incomplete plan.
7. **State the risks.** What could this break, which step is riskiest, and what did
   you consider and reject.
8. Write to `plan.md` (or `plan/<TRACKER-KEY>.md` — see "Concurrent sessions" above)
   using `${CLAUDE_PLUGIN_ROOT}/templates/plan.md`, including the "Files claimed"
   section, then get the engineer's approval before implementing.

## While implementing

- If the implementation departs from the plan, update `plan.md` **in the same commit**.
  The PR review compares the diff against the plan; silent drift will be flagged.
- Re-read `plan.md` before each new step in a long session. Do not work from memory
  of what you decided an hour ago.
- If the engineer corrects you on something non-obvious — a wrong assumption about the
  codebase, a convention you missed, a pattern you used incorrectly — note it as you go.
  Before the plan is marked done, propose one line for `CLAUDE.md`'s "Things Claude gets
  wrong here" section, worded plainly enough that the next session doesn't have to make
  the same correction twice. This is a proposal, not a silent edit: the engineer confirms
  it in the same review that approves the rest of the diff. A correction that is never
  captured costs the same lesson again next session; capturing it costs one line, once.

## Stack facts come from the profile, never from assumption

Read `.evidence/context/stack.md`, `deployment.md` and `design-system.md` before
planning. Never name a framework, runtime, datastore, deployment target or component
library that you have not confirmed from the profile or from a file you read. If the
profile carries an unresolved `[ASK]` in an area this change depends on, that is a
blocker — ask the human, do not fill the gap with the most likely answer.

## UI work

Plan each screen against APIs that already exist. If a screen needs an endpoint that
is not there, that is a separate plan item with its own tests, not a mock quietly
added to the client. Extend existing components before adding new ones; a new
component requires a written justification naming what was considered.

## Done means

`plan.md` (or `plan/<TRACKER-KEY>.md`) is committed, every path in it exists, every
requirement has a named test, "Files claimed" is filled in, and an engineer who has
never seen your session could implement it from the file alone.
