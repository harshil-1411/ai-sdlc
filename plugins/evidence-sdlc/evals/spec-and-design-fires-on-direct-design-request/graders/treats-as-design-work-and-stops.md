---
type: llm
---

This eval runs in an empty sandbox: there is no `.evidence/context/stack.md`
and no intent. In this organisation a direct design request with no process
vocabulary ("design the schema") is still design work governed by
spec-and-design, whose precondition is: if `.evidence/context/stack.md` does
not exist, STOP — produce no spec, design or schema — and run stack-discovery
first, because designing against unverified stack facts is how confidently
wrong designs get built.

PASS only if the response:
1. Says the stack profile (`.evidence/context/stack.md`, or "the repository
   profile" / "stack discovery hasn't run") is missing and that it will not
   design against unverified stack facts; AND
2. Does NOT produce the schema — no CREATE TABLE, no column/field list
   presented as the design (a one-line list of questions about the data is
   fine); AND
3. Names the next step: run stack discovery (and/or capture an intent / write
   a spec) before the schema is designed.

A `Risk tier: <n> — <reason>` line at the top is expected from the plugin but
not required by this grader.

FAIL if the response produces a schema or table design (even a "draft" or
"starting point"), or only asks generic clarifying questions without naming
the missing stack profile / discovery as the reason it stopped.
