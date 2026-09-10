---
name: toolchain-discovery
description: Establish which delivery tools a team actually uses — issue tracking, test management, source hosting, CI, support desk, cloud account, design system — and determine for each whether the agent can connect via MCP, CLI, REST, or not at all. Use this during repository onboarding, whenever a workflow needs a tool the session cannot currently reach, whenever someone asks whether Claude can talk to a given system, and before designing any cross-tool automation. Establish connectivity as fact, not assumption.
---

# Toolchain discovery and connectivity

A workflow that assumes it can write to a tool it cannot reach fails at the worst
moment — halfway through, having already made half the changes. Establish reach first.

## Step 1 — what the team actually uses

Read the evidence in the repository before asking anyone:
- Issue keys in commit messages and branch names reveal the tracker and its project keys
- Pipeline configuration reveals CI and deployment targets
- Test configuration and any result-reporter config reveal test tooling
- Package dependencies on a design system or component library reveal the design source
- Links in READMEs, PR templates and CODEOWNERS reveal the rest

Then confirm with a human. Tools people stopped using still leave traces.

## Step 2 — classify connectivity for each tool

For every tool, establish and record **one** of these:

| Class | Meaning | What to record |
| --- | --- | --- |
| `MCP-official` | Vendor ships an MCP server | Endpoint, transport, auth method, admin enablement needed, scopes |
| `MCP-community` | A third-party MCP server exists | Repo, maintainer, licence, last release — and a **security review requirement**, see below |
| `MCP-internal` | We build a thin MCP server over the vendor's REST API | Which endpoints, who owns it |
| `CLI` | A vendor CLI exists and is more token-efficient than MCP | Command, auth, whether it is on PATH |
| `REST-scripted` | No MCP; a reviewed script in the repo calls the API | Script path, credential source |
| `Manual` | No programmatic reach; a human does this step | Say so plainly in the workflow |

## Step 3 — the security decision on community MCP servers

**A community MCP server is a supply-chain dependency with credentials to a business
system.** In a regulated context this is a real decision, not a convenience one. Before any
community server is used:

- Named owner, licence, release cadence, and a read of what it actually does with
  credentials
- Scoped credentials only — a token limited to the projects and actions needed, never
  an admin token
- Route it through `strictKnownMarketplaces` / managed MCP allowlisting so individual
  engineers cannot add their own
- Prefer `MCP-internal` or `REST-scripted` over `MCP-community` for anything that
  **writes** to a system of record. Reading is a smaller risk than writing.

Record the decision and who made it. This is an entry in the toolchain profile, not a
conversation someone remembers.

## Step 4 — prefer CLI where it is cheaper

MCP loads tool schemas into context. For high-volume tools, a purpose-built CLI
invoked from a skill is often more token-efficient than an MCP server, and easier to
audit because the command is visible in the transcript. Some vendors now say so
themselves. Decide per tool, and record why.

## Step 5 — write the profile

Write `.evidence/context/toolchain.md` from the template. Every tool gets: what it is
used for, its class from Step 2, the credential source, the scope, who owns access,
and — critically — **what happens in the workflow when it is unreachable.**

## Rule

Never write a workflow step that assumes a tool is reachable without checking the
profile. If the profile says `Manual` for a step, the workflow says "hand to a human
here" rather than pretending.
