# External review packet: the traceability export

**Before you read further:** this material has not been reviewed by a regulator or
by any external quality body. See the note at the end of this document and
[`DISCLAIMER.md`](../DISCLAIMER.md) before you rely on anything here.

This document prepares a real review of a real artifact with a regulated-industry
quality/regulatory-affairs professional who has not seen this project before. It does
not attempt to conduct that review itself.

---

## a) What this is, in plain terms

When a development team builds software, they are supposed to be able to answer a
simple question for any given requirement: *what code implements this, what test
proves it works, and did that test actually pass?* In most organisations, answering
that question at release time means someone spends days manually cross-referencing
tickets, code, and test reports by hand — a process that is slow, easy to get wrong,
and produces a document that is already somewhat out of date by the time it's
finished.

The tool described here instead **reads the project's own records directly** —
its written requirements, its test files, and its change history — and produces a
table connecting them automatically. Nothing in that table is typed in by a person
after the fact; every entry is either found directly in the project's files, or is
explicitly marked as not found. The intent is that this table can be regenerated at
any time, and will always reflect what is actually true of the project's code and
tests at that moment — not what someone remembers or assumes to be true.

The output is a spreadsheet-style table (a CSV, importable into Excel or any
spreadsheet tool) with one row per requirement. Section (b) below walks through a
real one, column by column.

## b) A sample export, with commentary

This is the actual current output for one real requirement in this project, produced
by running the tool against this project's own files, unedited:

| Column | Value | What it means | Where it comes from |
| --- | --- | --- | --- |
| `tracker_key` | `TRACE-1` | The internal reference number for the piece of work this requirement belongs to. | Read from the commit history — the developer's own change-log entry names it. |
| `requirement_id` | `REQ-GATE-01` | A unique, stable identifier for this one requirement, so it can be referenced consistently everywhere (the requirement document, the test record, this table). | Assigned when the requirement was first written down. |
| `requirement_summary` | "The regression suite denies every documented true-positive case..." | A one-line description of what the requirement actually says, in the author's own words. | Copied verbatim from the requirements document. |
| `spec_commit` | `6571724b...` | The exact, permanent, unambiguous version-control record of the requirements document at the moment this requirement was written. | The version-control system's own change history — this is not something a person can quietly edit later without leaving a trace. |
| `implementing_commits` | `64ce2ca` | The specific code change(s) that were supposed to satisfy this requirement. | Also from version-control history, linked by the same internal reference number. |
| `test_case_id` | `GATE-TP` | The name of the specific test that is supposed to prove this requirement. | Named by the person who wrote the test. |
| `automated_test` | `plugins/evidence-sdlc/scripts/tests/gate-regression-tests.sh` | The actual test file, so anyone can go open it and read exactly what it checks. | The file path itself, as it exists in the project today. |
| `result` | `PASS (23/0)` | Whether that test actually ran and what happened. | The recorded output of actually running the test. |
| `risk_tier` | `1` | How much scrutiny this piece of work was judged to need before it shipped — routine internal work gets less ceremony than something touching a signature or an audit trail. | Assigned by the team using a documented set of criteria (what kind of change it is, what it touches). |
| `revalidation` | "None — no confirmed compliance framework applies" | Whether this change requires re-checking previously-approved work, and why or why not. | A stated judgement call, with the reason given explicitly rather than left implicit. |

**A candid note on this specific example:** running the tool's own gap-check against
this exact row today reports it as **not actually proven** — the test file named in
`automated_test` genuinely exists and genuinely passes, but it does not contain the
literal text `GATE-TP` (the value in `test_case_id`) anywhere in it, so the tool
cannot independently confirm the link a person asserted when they filled in this row.
This is not a mistake in this document — it is the tool correctly refusing to take a
person's word for something it cannot itself verify, which is precisely the property
a reviewer should be probing for. See section (c).

## c) What this cannot tell you

Read this section as seriously as section (b). A tool that only describes what it
does well is not trustworthy; a compliance audience should expect and check for this.

- **It cannot tell whether a requirement is any good** — only whether it exists and
  whether something claims to test it. A poorly-written, ambiguous, or wrong
  requirement will trace through this system just as cleanly as a correct one.
- **It cannot verify that a passing test actually tests the right thing.** A test can
  pass while checking the wrong condition entirely. This tool confirms a test *ran and
  reported success* — a human still has to have read that test and judged it sound.
- **It trusts the project's own written claims about which test proves which
  requirement**, and only checks that the named test file actually contains a
  reference to what it claims to prove — it does not re-derive that link from first
  principles. As section (b) shows candidly, when that check fails, the tool reports
  it — but the check itself is a minimum bar (does the connection exist at all), not
  a judgement of quality.
- **It cannot see inside an external issue-tracking or requirements system it has no
  direct access to.** If a project's requirements live entirely in a tool this system
  isn't connected to, it will honestly report that it found nothing, rather than
  guessing.
- **It does not know anything about your organisation's actual regulatory
  obligations.** It reports what it finds; deciding what that means for a given
  regulation, market, or customer contract is a human, organisational judgement this
  tool has no part in making.
- **It has not itself been audited or validated by any external party.** It was built
  and reviewed internally. Everything it reports should be treated as a starting point
  for a human's own verification, not as a substitute for it.
- **A clean-looking result does not mean nothing was missed.** It means nothing was
  found *within what this tool knows to look for*. A requirement written somewhere
  this tool doesn't scan, or tagged in a way it doesn't recognise, would be invisible
  to it — and would not appear as a gap, because the tool never saw it to begin with.

## d) Questions worth asking the reviewer

Framed so a comfortable "yes, that's interesting" isn't a complete answer:

1. **What would you STOP doing, specifically, if you trusted this?** Not "would this
   help" — name the actual manual step in your current process this would let you
   remove, and what you'd need to see first to actually trust removing it.
2. **Where in your current audit process would this table have caught something that
   was actually missed last time** — a real past instance, not a hypothetical one?
3. **What would make you NOT trust a row in this table, even though every cell is
   filled in?** What's the failure mode you'd be watching for that this document's
   limitations section (c) doesn't already name?
4. **If this table said a requirement was fully covered and you later found out it
   wasn't, whose job was it to have caught that, and at what point in your process?**
5. **What is the one thing about how your organisation currently proves compliance
   that this format cannot represent at all** — not "does poorly," but structurally
   cannot capture?

## e) This is unvalidated and unreviewed

**No part of this tool, this document, or the framework it comes from has been
reviewed, validated, or endorsed by any regulator, notified body, or external
compliance authority.** It was built and reviewed internally, by the team producing
it. Treat every claim in this packet as a starting point for your own organisation's
independent verification, not as a substitute for it.

See [`DISCLAIMER.md`](../DISCLAIMER.md) for the full statement, which applies in full
to this document and to the tool it describes.
