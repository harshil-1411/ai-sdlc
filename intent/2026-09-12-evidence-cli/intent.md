# Intent: The evidence CLI

Tracker: ITEM-1   Author: suparn.bector@msbdocs.com, maintainer   Date: 2026-09-12   Status: accepted

> **RETROSPECTIVE.** This intent is written after the CLI was already built and shipped
> (commit `9fab4e2`, "ITEM-1: Add the evidence CLI") and after a real correctness bug in
> it was found and fixed (`FIX-1`, `7207836`). It documents the problem honestly, as it
> was actually understood at build time and as it is understood now, rather than
> reconstructing a cleaner story after the fact. Where the original build skipped a step
> this framework otherwise requires — an intent before a spec, a spec before code — that
> is named plainly below, not hidden.

## Problem

Every other part of this framework is process: skills that shape how a session writes
requirements, designs, plans and reviews. None of it produces an artifact that exists
independently of the session that made it — something a compliance lead, an auditor, or
a CI pipeline could pick up and run without a Claude Code session attached. The
framework's central claim — "evidence can be derived from the artifact chain instead of
assembled by hand at release time" — was, until this CLI existed, untested. Nothing
actually attempted the derivation; every skill's traceability guidance was a description
of what SHOULD be derivable, not a working derivation.

Separately and concretely: `validation/traceability.csv` existed only as an empty
template (`plugins/evidence-quality/templates/traceability-matrix.csv`) — no repository
using this framework, including this one, had ever produced a populated, real export.

## Proposed outcome

A small, dependency-free command-line tool that a human (or a pipeline) can run without
any AI session involved, which:
- Preflights the environment every gate in this framework depends on (`doctor`)
- Builds a traceability graph from what is actually committed — no assumptions, no
  invented links (`scan`)
- Reports coverage gaps in a form that can block a release (`gaps`)
- Writes the traceability matrix in the framework's own documented column shape
  (`export`)

## Affected users and systems

- Anyone maintaining a repository that has adopted this framework, running the CLI
  locally or in CI.
- The external regulated QA/RA audience this framework is ultimately built for — the
  CLI's `export` output is the artifact that reaches them (see
  `docs/external-review-packet.md`).
- No production system, no customer-facing service. This tool reads a git working
  tree and writes only the file it is explicitly asked to write.

## Regulated record impact

No. The CLI itself creates no regulated record. It **reports on** whether regulated-adjacent
process controls (traceability, coverage) are being followed elsewhere in a repository —
it is an assessment tool, not a system of record.

## Compliance evidence impact

Yes, directly — this is the tool's entire purpose. `evidence export` is the mechanism
by which `evidence-package`'s "Export, do not assemble" rule becomes literally true
instead of aspirational.

## Data classification

None. The CLI reads only files already committed to the repository it runs in (source,
markdown, its own traceability CSV) and git's own commit metadata. No credentials, no
network calls, no external data of any class.

## Constraints

- Python 3, standard library only — no `pip install` step for a tool whose whole point
  is to work in an unfamiliar repository with as little friction as possible.
- No network access — the tool must be trustworthy to run against a repository nobody
  wants outbound connections from.
- Stayed inside the "~800 line" scope-discipline ceiling this framework applies to
  itself, though the item-1 correctness fix pushed the actual file to roughly 820-830
  lines; noted honestly in `cli/REVIEW-BRIEF.md` rather than silently exceeded.

## Out of scope

- A real YAML parser for `.evidence/adapter.yml` — the CLI's reader supports only the
  flat `key: value` / `key:` + `- item` list subset the framework's own generator
  produces. Documented, not hidden.
- Issue-tracker API integration (`requirements_source: tracker` reports plainly that it
  cannot reach a tracker rather than attempting to).
- Per-language static analysis for structural test-tag matching (item-1's fix uses a
  cross-language heuristic — common declaration/tag keywords in a small line window —
  not a real parser for any specific test framework).

## Open questions

1. Should `evidence gaps` be wired into this repository's own future CI once one exists
   (tracked as an existing `[ASK]` in `.evidence/context/stack.md`)? — awaiting:
   maintainer.
2. Is the ~800-line scope-discipline target still the right ceiling now that
   correctness fixes (structural matching, CSV corroboration, three exit codes,
   assessment-basis reporting) have pushed the file past it, or should a second file be
   split off before the next addition? — awaiting: whoever reviews `cli/REVIEW-BRIEF.md`.
3. Should the CLI's own retrospective chain (this intent, its spec) have been written
   BEFORE the code, per this framework's own `codebase-grounded-planning` precondition?
   The honest answer is yes, and it was not — this document is the acknowledgement of
   that gap, not a claim that the gap didn't happen.
