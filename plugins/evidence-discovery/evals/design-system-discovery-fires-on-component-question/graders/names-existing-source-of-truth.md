---
type: llm
---

PASS if the response identifies `@fixture/ui` (from `package.json`) as the
existing design-system package and names it as the thing to extend, rather
than proposing a brand-new component library or hand-rolled CSS for the
modal. This is a PASS even when the response also honestly flags that it
cannot confirm `@fixture/ui` ships a ready-made Dialog/modal component, that
its tokens are thin, or that no accessibility baseline exists, and asks a
clarifying question about where the real docs live — that caveating is the
"never guess, ask" behavior this skill is supposed to have, not a failure to
answer. Judge only whether `@fixture/ui` was named as the source of truth,
not the length, hedging, or confidence level of the surrounding prose.

FAIL only if the response ignores the existing `@fixture/ui` dependency
entirely and proposes building the modal from scratch or adopting a
different library as the actual recommendation.
