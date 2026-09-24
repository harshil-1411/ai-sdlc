---
type: llm
---

PASS if the response states that the branch name, every commit message, and
the PR title must all contain `PROJ-482`, and gives a branch name in the
`<type>/PROJ-482-<slug>` shape. Judge substance only, not length or hedging:
a response that also correctly flags `.evidence/context/toolchain.md` is
missing and that this is the skill's default shape rather than a
repo-confirmed convention is giving the right, honest answer, not failing to
answer — grade whether the three artifacts and the branch shape are stated
somewhere in the response, not whether every caveat was resolved.

FAIL only if the response actually omits the tracker key from any of branch
name, commit messages, or PR title anywhere in the response, or actually
invents a different key.
