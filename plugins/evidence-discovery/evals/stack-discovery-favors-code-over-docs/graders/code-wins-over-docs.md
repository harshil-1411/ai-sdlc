---
type: llm
---

PASS if the response identifies Express/Node (from `package.json` and
`src/server.js`) as the actual framework in use, and explicitly flags that
this disagrees with what `CLAUDE.md` claims (Django) — reporting the
disagreement as a finding rather than silently trusting either source alone.

FAIL if the response answers "Django" because that's what CLAUDE.md says, or
answers "Express" without ever mentioning the conflict with CLAUDE.md.
