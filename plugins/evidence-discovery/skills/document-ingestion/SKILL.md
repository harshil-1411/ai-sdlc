---
name: document-ingestion
description: Convert existing controlled documents — SOPs, validation protocols, requirement specifications, design documents, audit reports — into markdown the artifact chain can read, without losing their identity as controlled records. Use this at the start of any adoption where prior documentation exists in Word, PDF, spreadsheets or slides, whenever someone asks how existing procedures fit into this process, and whenever a change touches a requirement that only exists in a legacy document. Trigger on plain statements too: "we have existing SOPs in Word or PDF", "how do our current procedures fit into this process", "convert this document", "we already have a requirements spec, we're not starting from scratch" — even when it looks like the fastest path is to just retype it as markdown. Do this before writing new artifacts that would otherwise duplicate what already exists.
---

# Ingesting existing documentation

Every framework of this kind assumes work starts as markdown. On day one of a real
adoption that is false: the requirements, procedures and validation protocols already
exist, in Word and PDF, often under formal document control.

Skipping this step produces the worst outcome — a parallel set of markdown artifacts
that drifts from the controlled documents, so you now have two sources of truth and
neither is trustworthy.

## Rule 1 — conversion is not migration

Converting an SOP to markdown does **not** move document control. The controlled
document remains the controlled document. What you are creating is a machine-readable
working copy so the agent can read it.

Every converted file carries a header stating this:

```
> Source: <document ID> v<version>, <system of record>
> Converted: <yyyy-mm-dd> by <who>
> This is a working copy. The controlled document is the record.
> Re-convert when the source version changes.
```

Without that header, someone will eventually treat the markdown as authoritative and
edit it, and you will have a controlled procedure that quietly diverges from its
controlled copy.

## Rule 2 — decide the source of truth per document class

For each class of document, record one of three positions:

- **Repo is authoritative.** The markdown is the record; the legacy system holds a link.
  Only appropriate for documents nobody outside engineering depends on.
- **Legacy system is authoritative.** The markdown is a working copy that is re-derived
  on version change. This is the correct default for anything under document control.
- **Linkage only.** Both exist, each references the other's identifier. An honest
  interim state, and better than pretending you have resolved it.

Write the decision into `.evidence/context/` alongside the other profile files.

## How to convert

1. **Inventory first.** What exists, which system holds it, what version, who owns it,
   and when it was last reviewed. Documents nobody has touched in five years are a
   finding, not an input.
2. **Convert with a tool, not by retyping.** A document-to-markdown converter preserves
   structure — headings, tables, lists — which is what makes the result useful to an
   agent. Retyping loses structure and introduces transcription errors into a
   controlled record.
3. **Verify tables and numbered requirements survived.** These are where conversion
   fails most often, and they are exactly the parts that matter: requirement tables,
   control matrices, acceptance criteria, signature blocks.
4. **Preserve identifiers verbatim.** Requirement numbers, section numbers, document
   IDs and revision markers are how the traceability chain reaches back into the legacy
   record. Never renumber during conversion. If a numbering scheme is inconsistent,
   record that as a finding rather than tidying it.
5. **Do not summarise.** Convert. A summary is a new document with a new set of claims,
   and it will be read as if it were the original.
6. **Redact deliberately.** Some controlled documents contain customer names, pricing,
   or personal data that has no business being in a repository. Decide what is excluded
   and note the exclusion; do not silently drop content.

## What ingestion enables

- Existing requirements can be cited by `REQ-` IDs in new specs instead of restated.
- The compliance and validation skills can check a change against the procedure that
  actually governs it, rather than a generic checklist.
- Gaps become visible: procedures with no corresponding code, code with no governing
  procedure. Both are worth knowing about, and neither is discoverable while the
  documents are unreadable to the agent.

## Keeping it current

A converted copy of a superseded document is worse than no copy. Whichever tool holds
the controlled version, the working copy is re-derived when the version changes, and
the header records which version it reflects. If you cannot commit to that, choose
linkage-only instead and read the source document directly when it matters.
