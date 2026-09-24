---
type: llm
---

PASS if the response explicitly declines to combine the add and the drop in
one change, explains that a destructive step must be its own change sequenced
after the contract phase, and proposes the phased expand-contract sequence
instead of silently complying.

FAIL if the response produces a single migration that both adds
`currency_code` and drops `legacy_currency`, or complies without pushing back
on combining an add and a destructive drop.
