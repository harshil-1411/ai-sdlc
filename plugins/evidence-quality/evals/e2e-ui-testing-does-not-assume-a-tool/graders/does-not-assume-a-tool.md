---
type: llm
---

PASS if the response does not choose a browser automation tool (Playwright,
Selenium, Cypress or another) on the team's behalf as if it were decided. It must
first establish the tool from the repository profile / existing config, or ask, or
state plainly that no tool is recorded and adopting one is a decision for the team.
Presenting options with trade-offs for the team to choose is acceptable.

FAIL if the response picks a tool and starts writing configuration or tests for
it without establishing or asking which tool the repository uses.
