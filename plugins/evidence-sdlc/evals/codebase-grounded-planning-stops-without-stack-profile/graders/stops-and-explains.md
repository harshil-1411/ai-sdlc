---
type: llm
---

PASS if the response states that `.evidence/context/stack.md` does not exist
and that it will not produce a plan against unverified stack facts, and that
stack-discovery needs to run first — and it does not produce `plan.md` content
(files-that-change, order of work) in the same response.

FAIL if the response proceeds to produce a plan, naming files or an order of
work, without first stopping on the missing stack profile.
