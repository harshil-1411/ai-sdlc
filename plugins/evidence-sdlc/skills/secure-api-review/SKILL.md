---
name: secure-api-review
description: Apply the organisation application security standard to any endpoint, auth flow, storage change, dependency, or infrastructure change. Use this whenever code creates or modifies an API route, touches authentication, authorization, tenancy, tokens, key material, file upload/download, webhooks, or third-party calls; whenever an OpenAPI spec is generated; and whenever anyone asks for a security review, threat model, or pen-test prep. Also trigger on plain pre-PR review asks with no security vocabulary at all — "I added a new endpoint, can you review it", "review this before I open the PR", "can you review this handler/route", "review this diff", "PR review" — whenever the code shown or referenced is a route, handler, or endpoint. Applies whether the code is in the repository or pasted directly into the request.
---

# Secure API review

## Scope — what this skill is for

Official tooling already covers the common vulnerability classes. Anthropic's
`security-guidance` plugin warns on file edits and runs an agentic review at commit time
that traces data flow across files, catching injection, XSS, SSRF, hardcoded secrets,
insecure direct object references, auth bypass, unsafe deserialization and path
traversal. Install it and let it do that job.

**This skill covers what a generic scanner cannot know**: your tenancy model, your
definition of a regulated record, your audit-event requirements, your data-residency
rules, and your supply-chain policy. Where the two overlap, the generic finding is fine
and this skill adds the context that makes it actionable here.

Neither is a substitute for human review, SAST/DAST, dependency scanning, or
penetration testing. Both produce findings; a human decides.

This checklist assumes a multi-tenant product handling records that customers rely on.
Replace the examples with the two or three failures your product cannot have.

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

**Authentication and authorization**
1. Every endpoint requires the gateway JWT. No anonymous routes outside `/health`.
2. Authorization is checked server-side against the acting user's role *and* their
   tenant. Never trust a tenant ID supplied in the request body.
3. Object-level authorization: fetching any record by ID must verify ownership.
   Insecure direct object reference on a primary business entity is typically the
   highest-severity bug class in a multi-tenant product.

**Input and output**
4. Request bodies validated against the schema; unknown fields rejected, not ignored.
5. Uploaded files are treated as hostile: content-type verified from bytes not
   headers, size-bounded, rendered/parsed in an isolated path, never executed.
6. Fields classified `pii` or `signature-material` never appear in logs, error
   messages, traces, or analytics payloads.
7. Errors returned to the client are generic; detail goes to the server log.

**Secrets and crypto**
8. No credential, key, token, or connection string in source, config committed to
   git, test fixtures, or a comment. Key material comes from the KMS/HSM path only.
9. No hand-rolled crypto. No downgrade of an existing algorithm or key length
   without a written justification and QA/RA sign-off.

**Tenancy and data flow**
10. Every new query is tenant-scoped. A query without a tenant predicate on a
    multi-tenant table is a blocking finding.
11. New third-party calls, new egress domains, and new data-residency crossings are
    named explicitly. Regional deployments must not leak across regions.

**Agent and untrusted-content surface**
13. Any path where model-processed content originates outside the organisation — customer
    document text, ticket bodies, inbound email, webhook payloads, external PR content —
    is a trust boundary. Apply the `agent-trust-boundaries` skill. Flag as Critical any
    case where untrusted content reaches a model holding a state-changing tool with no
    intervening deterministic authorisation check.

**Supply chain**
12. New dependencies: state the package, why it is needed, its licence, its
    maintenance status, and whether an existing dependency already does the job.

## Output

For each finding: `Severity (Critical/High/Medium/Nit) | Location | What | Why it
matters here | Suggested fix`. Reserve Critical and High for anything that breaks
tenant isolation, record integrity, the audit trail, or authentication.

Report findings. Do not silently "fix and move on" for anything above Medium —
those need a human decision.
