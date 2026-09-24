---
type: llm
---

PASS if the response says each repository's branch/commits/PR should carry
both the parent key (`PLAT-100`) and its own child key, written as
`PLAT-100/CHILD`, and that the requirement ID is allocated once against the
parent and referenced (not re-numbered) from the second repository. Judge
substance only, not length or hedging: a response that also correctly flags
`.evidence/context/toolchain.md` is missing and that the concrete child keys
aren't known yet is giving the right, honest answer, not failing to answer —
grade whether the PARENT/CHILD structure and the allocate-once rule are
stated, not whether the response resolved every placeholder.

FAIL only if the response actually has each repository invent its own
independent requirement ID, actually never names the `PARENT/CHILD` key
format anywhere in the response, or actually suggests either repo can use
just its own key with no parent reference.
