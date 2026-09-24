---
type: llm
---

PASS if the response recommends writing characterization tests that pin down
current behaviour (including behaviour that might be a bug, marked as such)
before making any intended change, committed separately and run against
unmodified code first.

FAIL if the response jumps straight to refactoring or fixing the module
without first proposing characterization tests, or proposes changing behaviour
and writing tests in the same step.
