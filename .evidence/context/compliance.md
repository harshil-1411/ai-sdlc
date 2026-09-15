# Repository profile — industry and regulatory context

Project: evidence-chain   Established: 2026-09-10   Confirmed by: **unconfirmed — pending human answer**   Re-verify: annually

> This file is not inferred. Every entry has a person's name against it.

## Industry and markets
- [ASK] industry: not established — awaiting a named quality/compliance/legal owner's answer
- [ASK] market segments served: not established
- [ASK] jurisdictions — customers: not established
- [ASK] jurisdictions — data storage and processing: not established

Evidence gathered (context for the question, not an answer):
- This repository is itself a Claude Code plugin framework — templates, skills, hooks
  and agents distributed via a plugin marketplace. It is tooling *for* a software
  development lifecycle, not a product that stores customer data or serves end users
  directly.
- `DISCLAIMER.md` states explicitly: "Evidence Chain is not regulatory, legal, or
  compliance advice... Using it does not make any system, process, or organisation
  compliant with 21 CFR Part 11, EU GMP Annex 11, GAMP 5, ISO 13485, SOC 2, or any other
  framework." This is evidence about the *product's* posture toward regulation, not a
  substitute for the required human answer about this repo's own obligations.
- `plugins/evidence-compliance/skills/regulatory-controls/references/` ships
  pre-authored control-set summaries for: `21-cfr-part-11.md`, `eu-gmp-annex-11.md`,
  `gdpr.md`, `hipaa.md`, `iec-62304.md`, `iso-13485.md`, `pci-dss.md`, `soc2.md`. These
  are frameworks the *framework helps other repositories comply with* when installed
  there — not evidence that evidence-chain itself is subject to them.
- No customer data, payment data, health data, or personal data of any class is stored
  or processed by this repository. It contains no runtime service (see
  `.evidence/context/deployment.md`).

## Applicable frameworks

| Framework | Role | Control set to load | Named owner | Audited by / when | Confidence |
| --- | --- | --- | --- | --- | --- |
| — none established | — | — | — | — | [ASK] |

## Explicitly out of scope
| Framework | Why it does not apply | Confirmed by |
| --- | --- | --- |
| — none marked out of scope yet | Requires the same human confirmation as "applicable frameworks" — silence is not the same as "none apply" | [ASK] |

## Regulated record types for this product
> Used by every other skill. Specific enough that an engineer can decide unaided.

- [ASK] Not established. Candidate for discussion: if this repository's own governance
  process treats anything as a regulated record (e.g. `governance/records-retention.md`
  content, audit logs this framework's hooks produce for *other* repos), that should be
  named explicitly rather than assumed.

## Customer reliance
- [ASK] Do customers cite our controls in their own audits or validation? yes / no —
  not established. (Framing note: "customers" here would mean organisations installing
  and relying on evidence-chain's plugins inside their own regulated processes — a
  different question from whether evidence-chain itself is regulated.)
- [ASK] If yes: which controls, and what changes trigger customer notification

## Sensitive data classes handled
| Class | Where stored | Residency constraint | Framework driving the constraint |
| --- | --- | --- | --- |
| — none found | n/a | n/a | n/a |

## Existing certifications, validations and audit history
| Item | Status | Last assessed | Next due |
| --- | --- | --- | --- |
| — none found | n/a | n/a | n/a |

## Open questions — [ASK]
1. What industry and market segments does evidence-chain itself serve — is it purely
   open-source tooling with no direct regulatory exposure, or does the organisation
   distributing it (as a marketplace, a vendor, or internally) carry any obligation
   (e.g. software-as-a-medical-device tooling classification, export control, OSS supply
   chain policy)? — awaiting: quality/compliance/legal owner
2. Which jurisdictions is this repository itself published into or maintained from, and
   does that trigger any obligation independent of what it's used for? — awaiting: legal
3. Do any of the 8 pre-authored control-set references
   (`21-cfr-part-11`, `eu-gmp-annex-11`, `gdpr`, `hipaa`, `iec-62304`, `iso-13485`,
   `pci-dss`, `soc2`) need to be treated as authoritative for *this* repo's own
   governance (e.g. if evidence-chain's own release process is itself subject to a
   customer's supplier-audit expectations per `governance/supplier-audit-packet.md`)? —
   awaiting: quality/compliance owner
4. Do any downstream users (consuming repositories, customers, or internal teams) cite
   evidence-chain's own controls — its hooks, its audit-log mechanism, its templates —
   in their own audits or validation packages? If yes, this repo's own changes carry
   consequences inside someone else's compliance posture. — awaiting: quality/compliance
   owner
5. Is there a "none apply" answer intended here — i.e., has someone with the authority
   to say so already decided evidence-chain's own repository carries no regulatory
   obligation beyond general open-source licensing (MIT, per `LICENSE`)? If so, record
   who and when. — awaiting: quality/compliance/legal owner
