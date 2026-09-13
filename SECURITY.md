# Security

## Reporting a vulnerability

Report security issues privately via GitHub's private vulnerability reporting on this
repository, or to the address in the repository's contact information. Please do not
open a public issue for a vulnerability.

Include what you found, how to reproduce it, and what an attacker could achieve. We aim
to acknowledge within a few working days.

## Threat model for this project

This repository ships **configuration that grants and restricts an agent's behaviour**:
hook scripts that can allow or deny tool calls, managed-settings templates, and skills
that shape what an agent does. That makes a few classes of issue especially relevant:

- A hook that **fails open** — a gate that silently does not fire, for example because a
  script path is wrong or a dependency is missing. A policy gate that is quietly
  disabled is worse than no gate, because people trust it.
- A **permission or sandbox template that is more permissive than documented.**
- A **skill whose instructions could be steered** by content it is asked to process.
- Anything that would cause a **credential or secret to be read, logged, or transmitted.**

## What this project deliberately does not do

- It does not ship credentials, tokens, or endpoints for any third-party service.
- It does not include any MCP server implementation. `.mcp.json.example` is a template
  with placeholders; you decide what to connect and under what scope.
- It does not enable any connector by default.

## Using this safely

- **Read every hook script before installing it.** They run on your machine, in your
  repositories, with your permissions. That is the point, and it is also the risk.
- Verify each gate actually fires after installation. A mistyped path in settings leaves
  a gate silently disabled — check for the hook-error notice on first run.
- Treat any third-party MCP server as a supply-chain dependency holding credentials to a
  business system. Scope the credential; prefer read-only.
- **Hook execution failures are treated as non-blocking (allow) by the runtime.** A gate
  script that cannot execute — most commonly because the zip that shipped it lost the
  execute bit on extraction — does not deny the tool call, it lets it through silently.
  This is exactly the fail-open condition named above, and it will hit every adopter
  who unzips rather than clones. That is why every hook in this repository invokes its
  script via `bash ${CLAUDE_PLUGIN_ROOT}/scripts/<script>.sh` rather than relying on the
  script's own execute bit: `bash` running a file it can read does not depend on that
  file being independently executable. `evidence-sdlc`'s `preflight.sh` SessionStart
  hook additionally checks that `jq` resolves on PATH and that every gate script is at
  least readable, and says so loudly if not — but the `bash` wrapper is what removes the
  underlying cause.
- **A missing `jq` is a second, distinct fail-open vector from the one above** — every
  gate script shells out to `jq` to read its input, and `preflight.sh` can only ever
  warn about this (a `SessionStart` hook cannot deny a future tool call). Each of the
  six deny-capable gate scripts therefore now checks for `jq` itself, at the top, before
  parsing anything, and fails closed (denies) if it is absent, rather than falling
  through to an empty variable and an unintended default-allow.
