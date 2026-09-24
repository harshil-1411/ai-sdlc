---
name: traceability-ids
description: Enforce the single traceability identifier linking tracker issue, requirement, test case, branch, commit, pull request and evidence into one auditable chain. Use whenever a branch is created, a commit is written, a PR is opened, a test case is authored, or a traceability matrix is produced — and whenever anyone asks how a change is traced. Never produce any of these without the identifier.
---

# The traceability chain

An auditor's question is always the same shape: *show me this requirement, the code
that implements it, the test that proves it, and who approved it.* Answering that from
reconstruction takes days. Answering it from a chain takes seconds. The chain only
works if the identifier is on **every** artifact, without exception.

## The anchor

The **tracker issue key** is the anchor. Everything else references it. Read the exact key pattern from `.evidence/context/toolchain.md` — do not assume a
format, and do not assume every repository uses the same one.

```
Tracker issue  <KEY>
   ├── requirement IDs   REQ-<area>-<nn>   in spec.md, each citing <KEY>
   ├── test cases        in the test management system, each carrying <KEY>
   ├── branch            <type>/<KEY>-<slug>
   ├── commits           every message contains <KEY>
   ├── pull request      title contains <KEY>
   ├── automated tests   tagged with <KEY> and with their test-case ID
   └── evidence          test runs, review findings, approvals — all reachable from <KEY>
```

## Where the identifier must appear

| Artifact | Requirement |
| --- | --- |
| Branch name | Contains `<KEY>` |
| Every commit message | Contains `<KEY>` — enforced by hook |
| PR title | Contains `<KEY>` |
| `intent.md` / `spec.md` / `plan.md` | `Tracker: <KEY>` in the header |
| Requirement IDs | `REQ-<area>-<nn>`, each mapped to `<KEY>` in the spec table |
| Manual test case | A field on the case holds `<KEY>`; the case ID is recorded back on the issue |
| Automated test | Tagged with `<KEY>` **and** the manual case ID it automates, so a run maps to cases |
| Test run | Named with `<KEY>` and the build identifier |
| Traceability matrix row | `<KEY>`, REQ ID, test case ID, automated test, commit SHA, result |

For a change spanning repositories, `<KEY>` in every row above is `PARENT/CHILD` for
that repository — see "Changes that span repositories" below.

## Two-way linking is the point

One-way linking rots. Whenever you create a downstream artifact, **write the link
back**: when a test case is created, put its ID on the tracker issue; when a PR opens,
put its link on the issue; when a run completes, attach the result to the case and the
issue. If the tool is `Manual` in the toolchain profile, say so in the workflow rather
than silently skipping the back-link.

## Branching model

The chain works best with **short-lived branches off a single trunk**, each named for one
issue key, merged behind review.

Long-lived develop and release branches make the chain harder to follow: a change's
evidence gets spread across merge commits, and "which commit proves this requirement"
becomes genuinely ambiguous. If you maintain release branches for versions a customer
has validated, treat that as a narrow, documented exception with its own traceability
rules — not as the default model.

Whatever you choose, record it in the repository profile so the gates and the matrix
agree with reality.

## Changes that span repositories

A change crossing repositories uses one **PARENT** tracker key. Each repository's
branch, commits and PR carry both: the parent key and its own **child** key, written
as `PARENT/CHILD` (e.g. `PLAT-100/API-204`).

Requirement IDs are allocated once, against the parent, and referenced from each
repository — never re-numbered per repo. A requirement that a second repository also
implements cites the same `REQ-<area>-<nn>`, not a new ID local to that repo.

The parent issue records which repositories participate. A participating repository
with no linked child chain is an incomplete change, and a release finding — treat it
exactly as a `NO COVERAGE` requirement is treated within one repository.

Integration tests proving the cross-repo behaviour live in **one named repository**,
declared on the parent. "Both sides tested their half" is not proof the whole works —
each repository's unit and contract tests prove its own behaviour; only an
integration test that actually exercises the crossing proves the requirement the
parent issue exists for.

## Rules

- No key, no artifact. If someone starts work without a tracker issue, the first step
  is creating one — not proceeding and adding it later.
- One key per change **within a repository**. If a change genuinely serves two
  issues, it is two changes, or one issue with the other linked as related. Do not
  put two unrelated keys on one branch. A cross-repository change is the one
  exception, and even then carries exactly one parent key and one child key per
  repository, written as `PARENT/CHILD` — never more than that pair.
- Never invent a key. If you cannot reach the tracker to confirm the key exists, ask.
  A traceability chain anchored to a non-existent issue is worse than none.
- The chain is the audit evidence. Treat a missing link as a finding, not a tidiness
  issue.
