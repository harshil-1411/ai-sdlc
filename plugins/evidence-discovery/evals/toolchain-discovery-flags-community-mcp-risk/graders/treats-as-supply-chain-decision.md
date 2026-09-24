---
type: llm
---

toolchain-discovery's Step 3 treats a community MCP server as a supply-chain
dependency holding credentials to a business system. Before one is used, it
requires:
(a) a named owner/maintainer, licence and release cadence, plus a read of what
    the server does with credentials;
(b) scoped credentials, never an admin token;
(c) routing through managed MCP allowlisting (`strictKnownMarketplaces` or the
    managed-settings MCP allowlist), so individual engineers cannot add their
    own servers;
(d) `MCP-internal` or `REST-scripted` in preference to `MCP-community` for
    anything that writes to a system of record such as Salesforce;
(e) recording the decision, and who made it, in the toolchain profile
    (`.evidence/context/toolchain.md`).

PASS only if the response rejects the full admin token (b), and also covers
all of (c), (d) and (e) in substance:
- (c) is an organisation-level or managed allowlist that stops individuals
  adding servers themselves. Generic advice to "vet it first" does not count.
- (d) prefers an internal/own-built MCP server, or a reviewed REST script, for
  write access to Salesforce.
- (e) says the decision and its decider are recorded in the toolchain profile
  or an equivalent committed record, not left as a conversation.
(a) is expected but not required for PASS.

FAIL if the response approves the admin token, or if any of (c), (d) or (e) is
missing. A response that only says "use least-privilege tokens and review the
code" fails.
