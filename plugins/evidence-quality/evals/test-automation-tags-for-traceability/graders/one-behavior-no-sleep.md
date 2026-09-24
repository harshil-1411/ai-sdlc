---
type: llm
focus: { source: file, path: 'tests/export/throttle.test.ts' }
---

PASS if the new test's `test(...)` block is scoped to TC-118 ("rejected over
the limit") and its distinguishing, final assertions establish that outcome —
`allowed === false` and the correct `retryAfterMs`/wait-time — while proving
the boundary via the injectable `now` parameter, never a real sleep/timer.

A setup loop that calls the throttled function repeatedly to drive the
counter up to the limit before that final assertion is ordinary, idiomatic
arrange code for a boundary test — and it is normal and expected for each of
those setup calls to carry its own lightweight `expect(...allowed).toBe(true)`
sanity check that the request was accepted, so the test fails fast if the
setup itself is broken rather than silently reaching the wrong state. That
sanity-checked setup is NOT a second scenario and must not cause a FAIL by
itself — judge whether the test independently, fully verifies the
under-the-limit case as its own concern (see FAIL below), not whether an
`expect()` appears anywhere before the final assertion.

FAIL only if: the test also independently and fully verifies the
under-the-limit case as a complete concern in its own right — most tellingly,
by also asserting something about `retryAfterMs` for an accepted call (e.g.
that it is absent/undefined), which is what the *existing* TC-040 test above
it already covers and would make this test redundant with it rather than
scoped to TC-118 alone; or the test spans two `test(...)` blocks for this one
tracker item; or it waits on a real duration instead of the injectable clock.
