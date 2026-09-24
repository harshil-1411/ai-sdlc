# HIPAA Security Rule — electronic protected health information

> Scope: safeguards for ePHI where the organisation is a covered entity or business
> associate. The Privacy and Breach Notification rules are largely organisational and are
> not covered here. Source: drafted from public descriptions of the Security Rule.
> Owner: UNASSIGNED — the adopting organisation must assign a named owner before relying on this set (evidence doctor warns while unassigned).
> Last reviewed: never by an adopter; drafted 2026-09-24. **Not an authoritative interpretation.**

## Controls

| ID | Control | What to check in a change | Typical evidence |
| --- | --- | --- | --- |
| HIPAA-01 | Unique user identification | Every actor is individually identifiable; no shared accounts on paths touching ePHI | Identity model |
| HIPAA-02 | Access control | Access to ePHI limited by role and by relationship; enforced server-side | Authorisation tests |
| HIPAA-03 | Emergency access | A documented break-glass path exists and is itself logged | Break-glass test, log |
| HIPAA-04 | Automatic logoff | Sessions terminate after inactivity | Session config |
| HIPAA-05 | Encryption at rest and in transit | ePHI encrypted; addressable but treat as required | Config, tests |
| HIPAA-06 | Audit controls | Activity on systems containing ePHI is recorded and examinable | Audit-event tests |
| HIPAA-07 | Integrity | ePHI is not improperly altered or destroyed; alteration is detectable | Integrity checks |
| HIPAA-08 | Transmission security | ePHI in transit is protected against interception and modification | TLS config, tests |
| HIPAA-09 | Minimum necessary | Only the minimum ePHI needed is disclosed, returned by an API, or logged | Response shape review, log review |
| HIPAA-10 | Business associate flow-through | ePHI leaving to a third party is covered by an agreement, and the crossing is recorded | Integration spec, audit event |
| HIPAA-11 | Disposal | ePHI is disposed of securely when no longer required | Retention and deletion tests |

## Blocking classes

Any **Not met** on HIPAA-02, HIPAA-05, HIPAA-06, HIPAA-09 or HIPAA-10.

## Common misses

- **Minimum necessary in API responses.** An endpoint returning the full record because
  it was convenient is the most common finding in code, and the easiest to miss because
  nothing breaks.
- ePHI in application logs, traces or error payloads.
- Break-glass access implemented and never logged.
- A new analytics or monitoring integration silently becoming a business associate.
