---
type: llm
---

PASS if the response proposes converting the SOPs with a structure-preserving
tool (not retyping), keeping SharePoint as the controlled system of record
(conversion is not migration), adding a provenance header to each converted
file (source document ID/version, conversion date, "this is a working copy"),
and deciding a source-of-truth position (repo-authoritative /
legacy-authoritative / linkage-only) rather than treating the markdown copy as
the new authoritative record.

FAIL if the response treats this as a simple retype-into-markdown task, or
proposes making the markdown copy authoritative without addressing document
control.
