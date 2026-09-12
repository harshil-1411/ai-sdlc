---
name: toolchain-discovery
description: Establish which delivery tools a team actually uses — issue tracking, test management, source hosting, CI, support desk, cloud account, design system — and determine for each whether the agent can connect via MCP, CLI, REST, or not at all. Use this during repository onboarding, whenever a workflow needs a tool the session cannot currently reach, whenever someone asks whether Claude can talk to a given system, and before designing any cross-tool automation. Trigger on plain questions too: "can you access our Jira/GitHub/CI", "are we connected to X", "what's our tracker", "do we have a test management tool", "what CI do we use" — even when a README or onboarding doc appears to already say. Establish connectivity as fact, not assumption.
---

# Toolchain discovery and connectivity

A workflow that assumes it can write to a tool it cannot reach fails at the worst
moment — halfway through, having already made half the changes. Establish reach first.

## Do not offer — run

Do not ask "would you like me to run toolchain discovery?". If a workflow needs a
tool the session cannot currently reach, or someone asks whether Claude can talk to
a given system, and no profile exists, run the survey and answer from its results.

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

## Step 6 — generate `.evidence/adapter.yml`

The `evidence` CLI (`cli/evidence`) and other tooling need to know where this
repository's traceability chain actually lives, so they can work against
repositories that do not use this framework's own file layout. Write
`.evidence/adapter.yml` from `.evidence/adapter.example.yml`'s field list:

- `requirements_source` — `file_glob` if requirement IDs live in files here (spec
  documents, a requirements doc); `tracker` if they exist only in an issue
  tracker's API. Establish this from evidence (Step 1), not assumption.
- `spec_glob` — where those files live, if `file_glob`.
- `requirement_pattern` — the requirement ID shape actually used, grepped from
  real files, not the framework's own `REQ-<area>-<nn>` convention assumed by
  default.
- `tracker_pattern` — the issue key shape actually used, grepped from real
  commit messages and branch names.
- `test_dir_segments` — the actual test-location convention.
- `artifact_chain` — actual intent/plan file locations, if any exist.
- `test_results_location` — where CI publishes results, if anywhere locally
  reachable; `none` is a valid, honest answer.

Mark any field you could not establish as `[ASK]` rather than filling it with the
framework's own default, exactly as every other profile does. An `.evidence/adapter.yml`
full of unconfirmed defaults is worse than an honestly incomplete one — it tells the
CLI to look somewhere that might not be where this repository's evidence actually is.

## Rule

Never write a workflow step that assumes a tool is reachable without checking the
profile. If the profile says `Manual` for a step, the workflow says "hand to a human
here" rather than pretending.
