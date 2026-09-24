---
type: llm
---

PASS if the response states that `.evidence/context/stack.md` (the repository
profile) does not exist, that it will not produce a spec/design against
unverified stack facts, and that stack-discovery needs to run first — and it
does not produce a spec, schema, or design in the same response.

FAIL if the response proceeds to write requirements, a design, or a schema
without first stopping on the missing stack profile.
