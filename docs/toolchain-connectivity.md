# Toolchain connectivity — what connects, how, and what it costs you

Owner: Engineering Platform with Information Security. **Verify every line before you
act on it** — the MCP ecosystem moves fast and availability, auth mechanisms and
official/community status change. This is a starting map, not a current-state truth.

The output of this exercise per repository lives in `.evidence/context/toolchain.md`.
This document is the organisation-level view behind it.

---

## The classification that matters

Before anything else, split every tool into **read** and **write**.

Reading from a business system through an agent is a modest risk: worst case you leak
context into a session. Writing is different — an agent with write access to your
tracker, your test management system, or your source host can corrupt the record that
your traceability chain and your validation package depend on.

**Rule of thumb: prefer official or internally-built connectivity for anything the
agent may write to. Community MCP servers are acceptable for read, and require a named
security review and a scoped credential either way.**

---

## Category by category

### Source hosting and issue tracking

If your tracker and source host come from the same vendor, an official first-party MCP
server is usually available and is the right choice — it authenticates with the user's
own permissions, so every action is bounded by what that person could do anyway, and
vendor-side audit logging records the tool calls.

Two things to check before assuming it works:
- **Product coverage.** Vendors often ship tracker and wiki support before source-host
  support. Confirm the specific product you need is covered, not just the vendor.
- **Auth path.** Some products are reachable only on the API-token path and not the
  OAuth path, and the failure mode is silent: you connect successfully and simply do
  not see the tools for that product. If a product's tools are missing, suspect the
  auth path before suspecting your credentials.

There is also an admin prerequisite in most cases — an organisation admin must enable
the server, and sometimes enable token auth specifically. Budget for that conversation;
it is usually the long pole, not the technical setup.

**Where this lands in the SDLC:** intent capture reading tickets, spec writing back to
the issue, PR creation, pipeline status, and the two-way linking that `traceability-ids`
requires.

### Test management

Test management tools generally have a solid REST API and **no first-party MCP server**.
Several community servers exist and vary in quality.

Given that test cases and runs are validation evidence, this is the clearest case in
your stack for **build it internally or script it**:

- A thin internal MCP server, or a small reviewed CLI in the repo calling the REST API,
  gives you: a credential you scope yourself, an audit trail you own, and no third-party
  code holding a token to your evidence system.
- Whichever route, **the pipeline should own the write of results**, not an interactive
  session. Evidence should come from the toolchain.

One practical trap regardless of route: these APIs reject writes that do not match the
project's template and required custom fields, and the error is unhelpful. Discover the
field definitions once, record them in the repository profile, and have the authoring
skill read them rather than rediscovering them every session. The `testrail-authoring`
skill is written to do exactly this.

### Support desk

Support platforms are increasingly shipping first-party MCP servers, sometimes in early
access on higher tiers with API-key auth. If yours has one, it is the right route —
support tickets are the single richest source of `intent.md` material you have, and
support is the cheapest team to onboard.

**One caution specific to this category:** support ticket content is customer-written,
which makes it untrusted input. Any agent reading tickets is inside the boundary the
`agent-trust-boundaries` skill describes. Give a ticket-reading agent no write tools
beyond the ticket system itself, and never combine ticket reading with production data
access in one session. If you add such an agent to a plugin, also put its name
in the policy's `read_only_agents`. The gate engine then denies its file writes by
agent type, whatever its `tools` say ([policy-reference.md](policy-reference.md)).

### Cloud and infrastructure

Cloud vendors publish official MCP servers, and the ecosystem here is consolidating —
in at least one case the vendor now recommends a newer agent toolkit over its own
earlier MCP server collection.

Look specifically for the capability that matters most to you: **IAM condition keys or
equivalent that distinguish an agent's actions from a human's**, plus cloud-native audit
logging of those actions. That is the control that makes agent access to infrastructure
defensible rather than merely convenient. Where it exists, use the mechanism that
supports it even if an older option is more familiar.

Tier by environment, as in the deployment profile: agent may act freely in development,
prepares and waits in staging, and has no standing production credential at all.

Documentation-only servers are a separate and much safer thing — they read vendor docs,
hold no credentials, and are worth enabling widely.

### Browser and UI automation

A browser automation MCP server is genuinely useful for **exploration, test authoring,
and reproducing a reported defect** — an agent can drive the real UI and report what it
sees.

Two things worth knowing:
- Some maintainers now suggest a **CLI-plus-skill approach over MCP** for coding agents,
  on the grounds that MCP loads large tool schemas and verbose page snapshots into
  context while a purpose-built CLI is far more token-efficient. For high-volume use
  inside a coding session, that argument is sound. Evaluate both.
- **Pipeline test runs are scripted and deterministic.** An agent-driven browser session
  is not a test run and must never be recorded as one. Keep the two separate in your
  head and in your evidence.

### Design system

If the design system is a package, the agent reads it from the dependency tree and
needs no connector. If it lives only in a design tool, connectivity is a separate
question — and the more important finding is that a design system with no code
counterpart will drift no matter what you connect.

---

## The decisions to make once, centrally

1. **The allowlist.** Managed settings restrict which MCP servers may run and which
   marketplaces plugins may come from. Set this before rollout, not after someone adds
   a personal connector. `.mcp.json` is control plane: the gate engine won't let an
   agent add a connector to the repository itself ([managed-settings.md](managed-settings.md)).
2. **Credential scoping per tool.** One scoped credential per tool per purpose. Never an
   admin token because it was easier to provision.
3. **Read vs write, per tool, recorded.** With a name against each write decision.
4. **Community server review.** Who reviews, against what criteria, and how often
   re-reviewed. Treat it as the supply-chain dependency it is.
5. **Network egress.** The sandbox domain allowlist has to include every endpoint the
   approved connectors use, and nothing else. Agents can't write to a code host's API
   directly: the engine denies mutating `curl`/`wget` calls to GitHub and GitLab APIs,
   and merge or approve calls through `gh`.
6. **What happens when a tool is unreachable.** Per tool, in the profile. A workflow that
   assumes reachability fails halfway through, which is the worst place to fail.

## The honest limitation

Every connector you add increases the agent's tool surface and the number of places a
session can do something surprising. The correct number of connectors is not "all of
them." Start with the tracker and source host — those carry most of the traceability
value — then add test management, then support. Add each one when a workflow you
actually run is blocked without it.
