# Continuity, portability and cost

Owner: Engineering Director. Two board questions you will be asked; answer them before
they arrive.

## Continuity

If agent access is interrupted — vendor outage, contract lapse, regulatory action,
network isolation — teams must still be able to ship. Write down:

- **Degraded mode.** Which gates remain (all of them: plan, review, test, change control
  are process, not tooling) and which slow down (spec authoring, review passes, test
  generation). The SDLC does not change; the throughput does.
- **The single point of failure to avoid.** Do not let any gate become *only*
  executable by an agent. Every gate has a human procedure behind it. The gate
  engine's production-release rule checks for a human-set `RELEASE_APPROVAL`
  (engine cases V2G-06*) — the authorisation itself is a human act and remains valid
  without any tooling. Plan approval likewise has a terminal path
  (`evidence approve <KEY>`) and a GitHub-review path that work without an agent.
- **Rehearse once.** A half-day with agent access switched off tells you more than any
  plan document.

## Portability

Deliberate asymmetry in this framework:

| Asset | Portability |
| --- | --- |
| Skills, templates, artifact chain, REVIEW.md | Plain markdown. Portable to any agent that reads project rules. Low switching cost. |
| Subagent definitions | Markdown with light frontmatter. Mostly portable. |
| Hooks, managed settings, marketplace | Claude Code specific. Would need reimplementation. |
| Eval suite | Portable in content; harness is tool-specific. |

The valuable asset — your encoded standards, your Part 11 control checklist, your
traceability approach — is the portable half. That is deliberate. Keep it that way:
resist putting policy logic inside hook scripts when it belongs in a skill.

## Cost

Nobody budgets for this until month four. Do it now.

**Model tiering.** Mechanical passes (lint triage, changelog, test scaffolding,
formatting) go to a cheap fast model. Design, planning, the council, and compliance
review go to a capable one. This is the single largest cost lever and it costs nothing
to configure.

**Spend controls.**
- Per-project spend limits; alert before hard stop.
- The decision council is expensive by construction — five to six independent seats
  plus peer review. Gate it on genuinely hard-to-reverse decisions. If it is being
  convened weekly, it has become a ritual and is pure cost.
- Scheduled scans scoped to directories, not whole monorepos.
- Cap review passes on generated and vendored paths (already excluded in `REVIEW.md`).

**The metric that matters:** cost per merged change, tracked monthly against cycle time
and change-failure rate. Cost rising while cycle time falls is the programme working.
Cost rising while cycle time is flat means sessions are churning, which is usually a
missing feedback loop or a vague spec — a fixable engineering problem, not a budget one.
