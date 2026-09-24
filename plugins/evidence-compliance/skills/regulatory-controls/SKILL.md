---
name: regulatory-controls
description: Apply the control sets that actually apply to this project (read from the compliance profile, never assumed) to a design, code change or review, with a verdict and evidence for every control. Use when work touches a regulated record, audit trail, access control, retention, consent, personal, payment or health data, or record export, and whenever someone names a framework, an inspection or a certification.
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
expected rather than exceptional. Shipped sets:

| File | Framework |
| --- | --- |
| `21-cfr-part-11.md` | FDA 21 CFR Part 11 — electronic records and signatures |
| `eu-gmp-annex-11.md` | EU GMP Annex 11 — computerised systems |
| `iec-62304.md` | IEC 62304 — medical device software lifecycle |
| `iso-13485.md` | ISO 13485 — medical device quality management |
| `soc2.md` | SOC 2 — trust services criteria |
| `hipaa.md` | HIPAA Security Rule — ePHI |
| `pci-dss.md` | PCI DSS — payment card data |
| `gdpr.md` | GDPR — EU personal data protection |
| `iso-27001.md` | ISO/IEC 27001:2022 — Annex A development and change controls |
| `nist-ssdf.md` | NIST SP 800-218 v1.1 — Secure Software Development Framework |

**Check the set's owner line before using it.** If the file contains `Owner: UNASSIGNED`,
tell the human explicitly — in the report, not buried in it — that the control set has no
named owner and has never been reviewed by their organisation, so the verdicts rest on an
unreviewed interpretation. Do not stop the review over it, and do not fill in an owner
yourself; naming one is a human decision. (`evidence doctor` reports the same condition
as a WARN.)

## Step 4 — report

Produce one table per framework:

`Control | Verdict (Met / Not met / N/A) | Evidence`

Rules for this table:
- **Evidence is a pointer** — a file and line, a test name, a specific audit event, a
  configuration value. Never a description, never a promise.
- **"Not applicable" is a legitimate verdict**; silence is not. Every control gets a row.
- **"Looks correct" is not verification.** Verified means you found the check and it ran.
- Any **Not met** is a blocking finding. State plainly what would clear it.
- If the control set's owner is `UNASSIGNED`, say so at the top of that framework's
  table.

## Boundaries

You are not the regulatory authority, and neither is this framework. You surface
findings and evidence; the named owner in the compliance profile decides.

**Never write "this is compliant" as a conclusion.** Write which controls you verified,
against which framework, with what evidence, and which you could not verify. That
distinction is the difference between a useful finding and a liability.
