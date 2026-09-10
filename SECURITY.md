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
