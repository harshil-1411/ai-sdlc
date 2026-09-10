# SOC 2 — trust services criteria

> Scope: the criteria an auditor tests for a SOC 2 report. Security is always in scope;
> Availability, Confidentiality, Processing Integrity and Privacy are opt-in. Record which
> you carry. Source: drafted from public descriptions of the criteria. Owner: <name>.
> Last reviewed: <date>. **Not an authoritative interpretation.**

## Controls relevant to a code change

Most SOC 2 controls are organisational. These are the ones a diff can break.

| ID | Control | What to check in a change | Typical evidence |
| --- | --- | --- | --- |
| SOC2-01 | Logical access (CC6.1) | Access is authenticated and authorised; new endpoints default-deny; least privilege holds | Authorisation tests |
| SOC2-02 | Access provisioning and removal (CC6.2/6.3) | Role changes take effect; removal is complete and immediate | Access tests |
| SOC2-03 | Encryption (CC6.7) | Data encrypted in transit and at rest; no downgrade of algorithm or key length without justification | Config, TLS test |
| SOC2-04 | Change management (CC8.1) | Changes are authorised, tested, approved and traceable to a request | PR + tracker key + approval |
| SOC2-05 | Segregation of duties | The author of a change cannot approve it | Branch protection config |
| SOC2-06 | Logging and monitoring (CC7.2) | Security-relevant events are logged, retained, and monitored; logs are tamper-resistant | Log schema, retention config |
| SOC2-07 | Incident response (CC7.3/7.4) | Incidents detected, escalated and recorded | Incident records |
| SOC2-08 | Vulnerability management (CC7.1) | Dependencies scanned, findings triaged within policy, patches applied | Scan reports |
| SOC2-09 | Vendor management (CC9.2) | New third-party services and dependencies are assessed | Supplier review, SBOM |
| SOC2-10 | Backup and recovery (A1.2) | Backups occur and restores are tested | Restore evidence |
| SOC2-11 | Processing integrity (PI1) | Processing is complete, valid, accurate, timely and authorised | Validation and reconciliation tests |
| SOC2-12 | Confidentiality (C1) | Confidential data identified, protected, and disposed of per commitment | Classification, deletion tests |

## Blocking classes

Any **Not met** on SOC2-01, SOC2-03, SOC2-04 or SOC2-05.

## Common misses

- **Evidence of operation, not just design.** SOC 2 Type II tests that a control operated
  over a period. A control that exists but produces no dated evidence fails the audit
  even though the engineering is correct. Every control here needs a durable artifact.
- Segregation of duties defeated by an emergency-access path nobody documented.
- Logging that captures the event but not the actor.
