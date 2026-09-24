# Scenario: the sensor catches a stub, and the correction becomes a rule

**Who this is for:** anyone who wants to see two of this framework's quieter
mechanisms actually work together — the advisory sensor that checks a spec or
plan for an unfilled section, and the learning loop that turns a mid-session
correction into a line in `CLAUDE.md` so nobody makes the same correction twice.
Neither denies anything. Both are easy to miss if you've only read about the
seven deny-capable gates.

## The story

> "As a subscriber, I want my saved search results to refresh automatically
> every few minutes, so I don't have to reload the page to see new matches."

A Tier 2 feature (a new background-refresh code path, customer-visible) for a
product with no regulated-record obligation on this table.

## Walkthrough

**1 · Design, in a hurry.** `spec-and-design` writes `spec.md` for the feature.
The engineer is moving fast and leaves `## Areas of concern` exactly as the
template ships it:

```
## Areas of concern
<Every conflict between standards, every unsatisfiable constraint, each with the
named policy owner who must decide. Do not leave this empty by default.>
```

The intent was to come back to it after sketching the design. Nobody flagged
that out loud.

**2 · The sensor fires, right after the Write lands.** The gate engine's
PostToolUse sensor (`plugins/evidence-sdlc/scripts/engine/sensor.py`) reads the
file from disk, finds `## Areas of concern`'s body is still exactly the
template's own `<...>` placeholder, and emits an advisory note into
context — not a denial, nothing is blocked, the session keeps going:

> `intent/2026-11-03-saved-search-refresh/spec.md`'s "## Areas of concern"
> section is missing or still looks like the unfilled template placeholder.
> spec-and-design treats an empty section as suspicious; say so if there really
> are none. Advisory only -- nothing was blocked.

This is the sensor's entire job: it never asks permission and never stops
anyone, it just makes sure the gap doesn't quietly survive to review because
nobody happened to notice a placeholder sitting in a 90-line file.

**3 · The engineer fills in the real concern**, prompted by the note rather
than by a reviewer catching it three days later. This feature polls for
refreshed results on an interval, and the actual open question is real:
should the poll interval back off when a tab is backgrounded, or keep firing
at full rate and cost the customer's battery and this team's API quota for a
tab nobody is looking at? That's not a question the engineer can decide alone
— it trades UX freshness against infra cost — so it's routed to the named
platform-cost owner per `spec-and-design`'s existing rule, not silently
picked. `## Areas of concern` now reads as an actual finding, not a stub.

**4 · During implementation, a correction happens.** The agent's first pass at
the polling logic uses a fresh `setInterval` per mounted component, assuming
that's how this codebase's other polling features work. It isn't — this
product already has a shared `usePolling` hook specifically built to
centralize backoff and visibility-awareness, and the engineer corrects the
agent: "we have `usePolling` for exactly this, don't hand-roll another
interval." Nothing about this was in the plan, because nobody thought to
write down that the hook existed until the wrong assumption surfaced it.

**5 · The learning loop captures it**, per `codebase-grounded-planning`'s
"While implementing" rule: *"If the engineer corrects you on something
non-obvious — a wrong assumption about the codebase, a convention you missed,
a pattern you used incorrectly — note it as you go. Before the plan is marked
done, propose one line for `CLAUDE.md`'s 'Things Claude gets wrong here'
section."* Before `plan.md` is marked done, the agent proposes:

```
- Use the shared `usePolling` hook for any interval-based refresh; do not
  hand-roll `setInterval` per component. It already centralizes backoff and
  tab-visibility awareness.
```

This is a proposal sitting in the diff, not a silent edit to `CLAUDE.md`.

**6 · At review, the engineer confirms it** — the same PR review that
approves the polling implementation and the now-real "Areas of concern"
entry also approves this one line, and it lands in the same commit. No
separate ritual, no extra approval step invented for this.

**7 · The payoff, stated plainly by the rule itself:** *"A correction that is
never captured costs the same lesson again next session; capturing it costs
one line, once."* The next engineer — or the next session, possibly months
later — who builds a different interval-based feature reads `CLAUDE.md`
before writing a line of code and reaches for `usePolling` on the first pass,
because someone else's correction is sitting there instead of buried in a
closed session nobody can search.

## What this scenario deliberately shows side by side

Neither mechanism is a gate. The sensor never denied the `spec.md` write; the
learning loop never denied the implementation. Both are advisory, and both
still changed the outcome — the placeholder became a real finding, and the
wrong assumption became a rule — because each one surfaced something at the
exact moment a human was already looking, rather than relying on someone
remembering to check later.

## Read next

- [`spec-and-design`](../../../plugins/evidence-sdlc/skills/spec-and-design/SKILL.md)
  — the "Areas of concern" rule the sensor operationalizes
- [`codebase-grounded-planning`](../../../plugins/evidence-sdlc/skills/codebase-grounded-planning/SKILL.md)
  — the "While implementing" section with the learning-loop rule
- [`docs/gates-reference.md`](../../../docs/gates-reference.md) — the sensor's
  checks (under "Advisory hooks"), and why it's
  structurally incapable of denying anything
- [Scenario: a new user story](../new-feature-non-regulated/README.md) — the
  Tier 1 lightest path, for comparison against this Tier 2 one
