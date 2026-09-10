---
name: regulatory-controls
description: Apply the regulatory and standards control set that actually applies to this project to a design, a code change, or a review, and report a verdict with evidence for every control. Use this whenever work touches a regulated record, audit trail, authentication, access control, retention, consent, personal data, payment data, health data, or record export — and whenever anyone mentions compliance, an audit, an inspection, a certification, or a named framework. Read the applicable frameworks from the compliance profile; never assume which one applies.
---

# Regulatory controls

## Step 1 — load the right control set

Read `.evidence/context/compliance.md`. It lists the frameworks that apply to this
project, their role (legal obligation, contractual, certification held, alignment
claimed), and which reference control set to load from
`${CLAUDE_PLUGIN_ROOT}/skills/regulatory-controls/references/`.

**Do not proceed without it.** If the profile does not exist, run `compliance-discovery`
first. If it exists but the relevant framework is marked `[ASK]`, that is a blocker —
applying the wrong control set produces confident, wrong assurance, which is worse than
producing none.

If the profile says no framework applies, say so plainly and skip to the baseline
controls below rather than inventing an obligation.

## Step 2 — baseline controls, whatever the framework

These are worth checking on any product that keeps records people rely on, and most
frameworks are a stricter restatement of them:

| Control | What to check |
| --- | --- |
| Attribution | Every state change records who did it, in a form that cannot be repudiated or reassigned |
| Time integrity | Timestamps are server-side from a controlled source, never client-supplied, with timezone preserved |
| Audit completeness | The audit record is append-only, independently readable, and cannot be suppressed, batched away, or reordered by the change path |
| Access control | Authorisation enforced server-side, by role and by tenant, default-deny on new paths |
| Record integrity | Records remain retrievable and unaltered for their retention period, across migration and storage changes |
| Data minimisation | Sensitive fields do not appear in logs, traces, error messages or analytics |
| Retention and deletion | Retention is enforced, and deletion works where it is required |

## Step 3 — apply the framework control set

Load the reference file(s) named in the profile and work through every control. Common
sets ship in `references/`; see `references/README.md` for adding your own, which is
expected rather than exceptional.

## Step 4 — report

Produce one table per framework:

`Control | Verdict (Met / Not met / N/A) | Evidence`

Rules for this table:
- **Evidence is a pointer** — a file and line, a test name, a specific audit event, a
  configuration value. Never a description, never a promise.
- **"Not applicable" is a legitimate verdict**; silence is not. Every control gets a row.
- **"Looks correct" is not verification.** Verified means you found the check and it ran.
- Any **Not met** is a blocking finding. State plainly what would clear it.

## Boundaries

You are not the regulatory authority, and neither is this framework. You surface
findings and evidence; the named owner in the compliance profile decides.

**Never write "this is compliant" as a conclusion.** Write which controls you verified,
against which framework, with what evidence, and which you could not verify. That
distinction is the difference between a useful finding and a liability.
