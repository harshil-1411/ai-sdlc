# EU GMP Annex 11 — computerised systems

> Scope: computerised systems used as part of GMP-regulated activities in the EU.
> Complements Part 11 rather than duplicating it; where both apply, run both.
> Source: drafted from the public annex. Owner: <name>. Last reviewed: <date>.
> **Not an authoritative interpretation.**

## Controls

| ID | Control | What to check in a change | Typical evidence |
| --- | --- | --- | --- |
| A11-01 | Risk management | Change decisions are risk-based and the rationale is recorded | Risk assessment, tier decision |
| A11-02 | Supplier and service provider | Third-party components and services are assessed; agreements exist | Supplier assessment |
| A11-03 | Validation | Validation is current for the change; the lifecycle is documented | Validation impact, protocols |
| A11-04 | Data integrity | Data is protected against damage, whether accidental or deliberate | Integrity checks, backup test |
| A11-05 | Accuracy checks | Critical data entered manually is verified by a second method or person | Verification design |
| A11-06 | Data storage | Storage protects data; backups are verified by restore, not by success of the backup job | Restore test evidence |
| A11-07 | Printouts | Clear printed copies are obtainable, and changes since entry are indicated | Print/export test |
| A11-08 | Audit trails | Changes and deletions of GMP-relevant data are recorded with reason where required; audit trails are regularly reviewed | Audit-event test, review process |
| A11-09 | Change and configuration management | Changes are made only in a controlled manner | Change record, protected-path gate |
| A11-10 | Periodic evaluation | Systems are periodically evaluated for continued fitness | Review schedule |
| A11-11 | Security | Physical and logical controls restrict access; records of who did what are kept | Access control tests |
| A11-12 | Incident management | Incidents are reported, assessed for impact, and root cause determined | Deviation and CAPA records |
| A11-13 | Electronic signature | Signatures have the same impact as handwritten, are permanently linked, and record time and date | Signing flow test |
| A11-14 | Batch release | Where used for certification, only the authorised person can certify, and this is clearly recorded | Authorisation test |
| A11-15 | Business continuity | Continuity arrangements exist for system unavailability | Continuity plan, rehearsal record |
| A11-16 | Archiving | Archived data remains readable and accessible; readability is checked on system change | Archive readability test |

## Blocking classes

Any **Not met** on A11-04, A11-08, A11-09, A11-11 or A11-13.

## Common misses

- **Audit trail review** treated as a system feature rather than a periodic activity with
  evidence that it happened.
- Backups reported as successful without a **restore** ever being tested.
- **Reason for change** required on certain data edits and not captured in the UI.
- Archive readability quietly broken by a serialization change, discovered years later.
