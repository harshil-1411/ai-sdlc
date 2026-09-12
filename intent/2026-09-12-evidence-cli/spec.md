# Spec: The evidence CLI (retrospective)
Tracker: ITEM-1   From: intent/2026-09-12-evidence-cli/intent.md   Risk tier: 1

Tier 1 — Routine: internal tooling, no regulated record, no production code path.
Stated per risk-tiering before the requirements below, as with every spec in this
repository, even though (per the intent's own admission) this spec was written after
the code, not before it.

**RETROSPECTIVE.** Requirement IDs below are numbered to match actual, already-built
behaviour, verified either by an automated fixture (`cli/tests/test_cli_fixtures.sh`)
or by manual command runs pasted into this session's transcript and the `FIX-1` /
`ITEM-1` commit messages. Where only the latter exists, it is marked so plainly in the
Proof table rather than implied to be automated.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Requirements

| ID | Requirement | Source | Acceptance |
| --- | --- | --- | --- |
| REQ-CLI-01 | `evidence gaps` produces exactly three, mutually exclusive outcomes: exit 0 (assessed, clean), exit 1 (assessed, gaps found), exit 2 (nothing to assess — zero requirements found anywhere). No two of these ever render as the same output. | intent.md Proposed outcome | Three fixtures, one per exit code, each asserting the exact exit status. |
| REQ-CLI-02 | A requirement counts as covered by a test only when there is a structural tie between the requirement ID and a real test declaration or an explicit tag — on the same line, or the line immediately before/after. Mere presence of the ID anywhere else in a test-shaped file is not coverage. | intent.md Problem (the false-"fully covered" bug) | A fixture with a genuine structural tag passes as covered; a fixture with only a loose, same-file mention still reports uncovered. |
| REQ-CLI-03 | A `validation/traceability.csv` row naming a `requirement_id` and a `test_case_id` counts as coverage only if the named `automated_test` file exists and its content contains the `test_case_id` or `requirement_id` verbatim. An uncorroborated claim is reported uncovered, with the specific reason named. | intent.md Problem | A fixture with an uncorroborated CSV claim reports uncovered with the reason string present; a fixture with a corroborated claim reports covered. |
| REQ-CLI-04 | `evidence doctor` checks jq-on-PATH, gate-script readability, hooks.json validity and referenced-script existence, `.evidence/context/` profile presence, unresolved `[ASK]` count, and profile staleness (>~6 months), and exits non-zero if any check marked critical fails. | intent.md Proposed outcome | [NEEDS VERIFICATION — manual only] Verified by direct runs in this session: jq removed from PATH -> FAIL, exit 1; a hooks.json referencing a deleted script -> FAIL, exit 1; a deleted `.evidence/context/` -> FAIL, exit 1. No automated fixture exists yet. |
| REQ-CLI-05 | `scan`, `gaps` and `export` read `.evidence/adapter.yml` when present (tracker_pattern, requirement_pattern, spec_glob, test_dir_segments, requirements_source) and fall back to this framework's own layout when absent; `requirements_source: tracker` is reported plainly rather than silently returning zero requirements. | intent.md Out of scope (no tracker API) | [NEEDS VERIFICATION — manual only] Verified with a synthetic `requirements_source: tracker` repository in this session (commits/tracker keys still scanned; requirements correctly report 0 with an explanatory message). No automated fixture exists yet. |
| REQ-CLI-06 | `evidence export` is append-safe: a requirement not touched by the current scan keeps its existing traceability row unchanged rather than being rewritten or dropped. | intent.md Proposed outcome | [NEEDS VERIFICATION — manual only] Verified by running `export --write` twice in a row against a synthetic repository and confirming no duplication or data loss. No automated fixture exists yet. |
| REQ-CLI-07 | `scan --repos <dir>` and `gaps --repos <dir>` walk sibling git repositories, join their tracker keys on the PARENT half of a `PARENT/CHILD` pair, and `gaps --repos` reports requirements covered in some participating repositories but not others as a distinct section, with a non-zero exit when any exist. | intent.md Affected users and systems | [NEEDS VERIFICATION — manual only] Verified with a synthetic two-repository scenario in this session (one requirement covered in one repo, not the other; cross-repo gap correctly reported, exit 1; resolved to exit 0 once both repos were covered). No automated fixture exists yet. |

## Design

Four subcommands (`doctor`, `scan`, `gaps`, `export`) sharing one `build_graph()`
function that reads the repository once into an in-memory structure (`requirements`,
`tests`, `commits`, `traceability_rows`), which `gaps` and `export` both consume. See
`cli/REVIEW-BRIEF.md` for the full structural walkthrough — that document exists
specifically so a reviewer does not have to reverse-engineer this from the source.

## Regulatory control impact

No framework is confirmed applicable to this repository's own governance
(`.evidence/context/compliance.md`, all rows `[ASK]`), and this change touches no
regulated record regardless of that.

| Framework | Control ID | Applies? | How it is satisfied | Evidence |
| --- | --- | --- | --- | --- |
| N/A | N/A | No | No confirmed framework; no regulated record touched | intent.md "Regulated record impact" |

## Evidence impact

New requirement entries REQ-CLI-01 through REQ-CLI-07 are added retrospectively. No
prior entries existed for the CLI. Re-verification: none — Tier 1.

## Diagrams

None needed — see `cli/REVIEW-BRIEF.md`'s data-flow walkthrough instead, which serves
the same purpose in prose for a four-function command-line tool with no service
boundary, sequence, or deployment topology to depict.

## Security design

N/A. No network egress, no credential handling, no new trust boundary. Reads only
files already present in the working directory; writes only the file it is explicitly
asked to write (`export --write`).

## UX

<Delete rows that do not apply; do not delete the table.>

| State / concern | Behaviour |
| --- | --- |
| Loading | N/A — the CLI runs to completion or exits; there is no long-running interactive state. |
| Empty | `scan`/`gaps` on a repository with zero requirements print a distinct, honest message ("Nothing to trace" / "No requirements found... Nothing to assess") rather than an empty-looking success. |
| Error | Malformed adapter YAML, an unreadable file, or invalid JSON in a hooks.json is reported by name, never silently swallowed into an empty result. |
| Success | `RESULT:` line states plainly what was found and what it means for a pipeline (block or proceed). |
| Partial / stale data | Unreadable files are counted and reported (`N unparseable file(s) skipped`) rather than silently treated as empty. |
| Edge cases (long values, zero, maximum, unusual input) | Zero requirements is its own exit code (2), never conflated with zero gaps (0). |
| Responsive behaviour | N/A — terminal output, not a layout. |
| Keyboard navigation | N/A — no interactive UI. |
| Screen reader / assistive technology | N/A — plain stdout/stderr text, readable by any terminal or screen reader without special handling. |
| Focus management | N/A — no UI. |

Component reuse: N/A — no design system applies to a command-line tool.

## Areas of concern

- **This spec was written after the code**, violating `codebase-grounded-planning`'s
  own precondition in spirit (plan before code) even though that skill technically
  applies to `plan.md`, not `spec.md`. Named honestly in intent.md's Open Questions.
  Owner: whoever reviews this retrospective chain.
- **Four of seven requirements (REQ-CLI-04 through -07) have no automated test**, only
  manual verification from this session's transcript. This is the accurate state, not
  a gap I am hiding — see `cli/REVIEW-BRIEF.md` section (d) and the dogfood
  `evidence gaps` run in this same commit's message.
- **The ~800-line scope-discipline target was exceeded** (the file is now ~820-830
  lines after the item-1 correctness fix). Owner: whoever next proposes adding to
  `cli/evidence` should read `cli/REVIEW-BRIEF.md`'s note on this before adding more.

## Rejected alternatives

Considered writing this spec BEFORE further modifying the CLI, deferring the item-1
correctness fix until the retrospective chain existed. Rejected: item-1's priority was
explicit and time-sensitive (a real correctness bug reporting false compliance
coverage), and the task itself sequenced the fix before the review-prep work. The
retrospective framing here is the honest resolution of that ordering, not a
justification for skipping the chain entirely.
