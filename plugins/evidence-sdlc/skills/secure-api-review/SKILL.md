---
name: secure-api-review
description: Review an endpoint, auth flow, storage change, dependency or infrastructure change against the OWASP API Security Top 10 and the organisation's security profile. Use when code creates or changes an API route, authentication, authorization, tenancy, tokens, key material or file upload, when an OpenAPI spec is generated, and on "security review", "threat model", or "I added an endpoint, can you review it" — including code pasted into the request.
---

# Secure API review

## Scope — what this skill is for

Official tooling already covers the common vulnerability classes. Anthropic's
`security-guidance` plugin warns on file edits and runs an agentic review at commit time
that traces data flow across files, catching injection, XSS, SSRF, hardcoded secrets,
insecure direct object references, auth bypass, unsafe deserialization and path
traversal. Install it and let it do that job.

**This skill adds what a generic scanner cannot know**: your tenancy model, your
definition of a regulated record, your audit-event requirements, your data-residency
rules, and your supply-chain policy. Where the two overlap, the generic finding is fine
and this skill adds the context that makes it actionable here. The OWASP API Top 10
is still walked explicitly below, so a gap in either tool is visible.

Neither is a substitute for human review, SAST/DAST, dependency scanning, or
penetration testing. Both produce findings; a human decides.

## Read the organisation's specifics first

The checks below are generic until the profile fills them in. Read
`.evidence/context/stack.md` (auth mechanism, gateway, public/unauthenticated routes,
key-management service, tenancy model) and `.evidence/context/compliance.md` (data
classes, audit-event requirements, residency rules, sign-off roles). Where a check needs
a fact the profile does not state, mark it `[ASK]` in the output and still run the rest.
Never assume a JWT gateway, a health-check path, a KMS, or a data-class name.

## Review the code you were given

If the handler, route, or diff under review is included directly in the
request — pasted inline, in a code block, or as a diff — review that code.
Do not require locating a matching file on disk before reviewing it. A phrase
like "I added a new endpoint, can you review it" describes a change that
already happened in the author's own working copy; it does not mean the code
is present in *this* session's checkout, and an empty or unrelated repository
here is not evidence that the change doesn't exist. If you cannot find the
file, say so as a one-line caveat and still run the full review against the
code you were given — never decline to review pasted code just because a
matching file search came up empty.

## Checks

Checks 1–10 are the OWASP API Security Top 10 (2023). Checks 11–17 cover what a generic
list cannot know about this system. Cite the check number in every finding.

**OWASP API Security Top 10 (2023)**
1. **API1 Broken object level authorization.** Every fetch, update or delete by ID
   verifies the caller may act on *that* object, server-side. An unscoped lookup of a
   primary business entity is typically the highest-severity bug in a multi-tenant
   product.
2. **API2 Broken authentication.** Every route requires the authentication the profile
   names, except the unauthenticated routes it lists. Token lifetime is bounded; refresh
   and revocation work (logout, password change, role removal and offboarding invalidate
   live sessions and tokens); signatures, `aud`, `iss` and expiry are verified; no
   credential or token in a URL.
3. **API3 Broken object property level authorization.** Request bodies are validated
   against the schema and unknown or read-only fields are rejected, not ignored (mass
   assignment). Responses return only the fields the caller's role may see — no
   serialising the whole model.
4. **API4 Unrestricted resource consumption.** Rate limits and quotas per caller and per
   tenant; bounded page size, request body, upload size, query complexity and batch
   length; timeouts on downstream calls; costly operations (email, SMS, exports, model
   calls) limited per caller.
5. **API5 Broken function level authorization.** Admin and cross-tenant functions check
   role server-side; the role and the tenant come from the authenticated identity, never
   from the request body or a client-set header.
6. **API6 Unrestricted access to sensitive business flows.** Flows that are harmful when
   automated (sign-up, purchase, invite, approval, bulk export) have abuse controls
   beyond auth: velocity limits, step-up, or human confirmation.
7. **API7 Server-side request forgery.** Any URL, host or file reference the caller
   supplies is validated against an allowlist before the server fetches it; internal
   and metadata addresses are unreachable.
8. **API8 Security misconfiguration.** CORS allows only named origins and never
   reflects arbitrary origins with credentials; cookie-authenticated state-changing
   routes have CSRF protection (SameSite plus a token or origin check); security headers
   are set; TLS only; errors to the client are generic with detail in the server log;
   debug endpoints and verbose stack traces are off outside development.
9. **API9 Improper inventory management.** New or changed routes appear in the API
   description (OpenAPI or equivalent); old versions have a stated deprecation path;
   no undocumented, test or shadow routes are exposed.
10. **API10 Unsafe consumption of APIs.** Responses from third-party APIs are validated
    like user input — schema, size, redirects, timeouts — and never trusted for
    authorization decisions. Apply `integration-change` for the availability side.

**Organisation specifics (from the profile)**
11. **Tenancy.** Every new query on a multi-tenant table carries a tenant predicate. A
    missing one is a blocking finding.
12. **Sensitive data.** Fields in the data classes `compliance.md` defines never appear
    in logs, error messages, traces or analytics payloads. Uploaded files are treated as
    hostile: type verified from bytes, size-bounded, parsed in isolation, never executed.
13. **Audit events.** Every state change to a regulated record, every authentication
    event, every permission change and every denied authorization attempt emits the
    audit event `compliance.md` requires, with actor, tenant, target, action, outcome and
    timestamp, and no sensitive values. A path that changes a regulated record without
    one is Critical.
14. **Secrets and crypto.** No credential, key, token or connection string in source,
    committed config, fixtures or comments. Key material comes only from the
    key-management path the profile names. No hand-rolled crypto; no downgrade of an
    algorithm or key length without a written justification and the sign-off
    `compliance.md` requires.
15. **Data flow and residency.** New third-party calls, egress domains and residency
    crossings are named explicitly; regional deployments do not leak across regions.
16. **Agent and untrusted content.** Any path where model-processed content originates
    outside the organisation — customer documents, tickets, inbound email, webhook
    payloads, external PR content — is a trust boundary. Apply `agent-trust-boundaries`.
    Critical if untrusted content reaches a model holding a state-changing tool with no
    deterministic authorisation check between them.

**Supply chain**
17. New dependencies: the package, why it is needed, its licence, its maintenance
    status, and whether an existing dependency already does the job.

## Output

For each finding: `Severity (Critical/High/Medium/Nit) | Check # | Location | What | Why
it matters here | Suggested fix`. Reserve Critical and High for anything that breaks
tenant isolation, object or function authorization, authentication, record integrity or
the audit trail. List every `[ASK]` the profile left open.

Report findings. Do not silently "fix and move on" for anything above Medium —
those need a human decision.
