---
type: llm
---

PASS if the response assigns each requirement to the lowest test layer that can
actually prove it (e.g. REQ-AUTH-02's audit event is proven at
integration/API, not forced through a full end-to-end UI journey unless
nothing lower can prove it), and does not propose gating either requirement on
an aggregate code-coverage percentage.

FAIL if every requirement is pushed to end-to-end/manual by default with no
justification, or the response proposes a coverage-percentage gate.
