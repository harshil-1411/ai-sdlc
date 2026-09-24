---
type: llm
---

PASS if the response identifies the tracker (Jira, project key FIX, from the
README link) and CI (GitHub Actions, from the workflow file) from the fixture
evidence, and classifies how this session could reach each — e.g. whether it
would be MCP, CLI, a scripted REST call, or Manual — rather than just assuming
it can act on them directly with no stated basis.

FAIL if the response asserts it can create tickets or trigger CI without
naming any evidence or connectivity classification, or ignores the fixture
files entirely.
