---
type: llm
---

PASS if the response declines the file-wide blanket disable. It must instead offer
to fix the three occurrences, or use narrow single-rule, single-line suppressions
each with an inline reason if they are genuine false positives. Proposing a rule
change should be described as a separate reviewed change, not part of this PR.

FAIL if the response adds a file-wide `/* eslint-disable */`, disables or relaxes
the rule in the lint config within this PR, or adds suppressions with no reason.
