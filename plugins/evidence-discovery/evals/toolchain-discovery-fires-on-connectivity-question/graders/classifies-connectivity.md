---
type: llm
---

The fixture shows Jira (project key FIX, linked in `README.md`) and GitHub
Actions (`.github/workflows/ci.yml`). toolchain-discovery classifies every tool
into exactly one connectivity class from a fixed vocabulary: `MCP-official`,
`MCP-community`, `MCP-internal`, `CLI`, `REST-scripted`, `Manual`. It records,
for each tool, what the workflow does when the tool is unreachable ("hand to a
human here"). The profile is `.evidence/context/toolchain.md`.

PASS only if the response does all of the following, anywhere in the reply:
1. Identifies Jira (key FIX) and GitHub Actions from the fixture files, citing
   them.
2. Assigns each of the two tools a connectivity class using that vocabulary's
   names (e.g. "Jira: `Manual` today, `MCP-official` if an admin enables the
   Atlassian server"). A current class plus a possible future class is fine.
   Loose phrasing like "no integration" or "I can't reach it" with no class
   name does not count.
3. States, for at least one tool that is not currently reachable, what happens
   in the workflow: a human does that step, or it is handed off to a human.
4. Names `.evidence/context/toolchain.md` as where this is recorded (written,
   would be written, or proposed).

FAIL if either tool has no class from the vocabulary; if the response asserts
it can create tickets or trigger CI with no stated basis; if the unreachable
fallback is never stated; or if the toolchain profile is never mentioned.
