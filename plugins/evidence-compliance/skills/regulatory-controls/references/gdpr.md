# GDPR — personal data protection

> Scope: processing of personal data of people in the EU/EEA. Similar structures apply
> under UK GDPR and several other regimes; adapt rather than duplicate. Source: drafted
> from public descriptions.
> Owner: UNASSIGNED — the adopting organisation must assign a named owner before relying on this set (evidence doctor warns while unassigned).
> Last reviewed: never by an adopter; drafted 2026-09-24.
> **Not an authoritative interpretation, and not legal advice.**

## Controls

| ID | Control | What to check in a change | Typical evidence |
| --- | --- | --- | --- |
| GDPR-01 | Lawful basis | Every new processing purpose has a recorded lawful basis. A new purpose is a change, even on data you already hold | Processing record |
| GDPR-02 | Data minimisation | Only data necessary for the purpose is collected, returned, logged or retained | Field-level review |
| GDPR-03 | Purpose limitation | Data collected for one purpose is not reused for another without a basis | Design review |
| GDPR-04 | Storage limitation | Retention period defined and enforced for each data class | Retention config, deletion test |
| GDPR-05 | Data subject rights | Access, rectification, erasure, portability and objection are technically possible — including in backups, caches, logs and analytics | Rights-request test |
| GDPR-06 | Security of processing | Appropriate technical measures; encryption and pseudonymisation where proportionate | Config, tests |
| GDPR-07 | Privacy by design and default | Privacy considered in the design, and the default setting is the private one | Spec section |
| GDPR-08 | Transfers | Personal data leaving the EEA has a transfer mechanism; residency constraints enforced technically | Residency config, integration spec |
| GDPR-09 | Processors | Third parties processing personal data are under a processor agreement; sub-processors disclosed | Vendor records |
| GDPR-10 | Records of processing | The processing record is updated when processing changes | ROPA entry |
| GDPR-11 | DPIA | High-risk processing triggers an impact assessment before it starts | DPIA |
| GDPR-12 | Breach readiness | Personal data breaches are detectable and reportable within the required window | Detection, runbook |

## Blocking classes

Any **Not met** on GDPR-01, GDPR-04, GDPR-05 or GDPR-08.

## Common misses

- **Erasure that misses the copies** — search indexes, caches, analytics warehouses,
  backups, and the audit trail. The audit trail case genuinely conflicts with retention
  obligations elsewhere; that conflict is a decision for the named owner, not for an
  engineer to resolve quietly in code.
- A new third-party SDK becoming a processor without anyone noticing.
- Residency enforced by configuration convention rather than by a technical control.
- A new analytics event carrying an identifier that makes previously anonymous data
  personal again.
