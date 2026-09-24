---
type: llm
---

PASS if the response declines to propose a fix given how little was provided,
and instead asks for the smallest set of missing essentials (expected vs.
actual behaviour, logs/errors, reproduction steps, when it started / what
changed) in one round rather than proposing a speculative fix.

FAIL if the response proposes a specific code fix or diagnosis despite having
none of: expected behaviour, actual behaviour, logs, repro steps, or a
timeline.
