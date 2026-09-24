# 21 CFR Part 11 — electronic records and electronic signatures

> Scope: FDA-regulated electronic records and signatures used under a predicate rule.
> Not covered: the predicate rule itself, or system validation as a whole — Part 11 sits
> on top of those. Source: drafted from the public regulation text.
> Owner: UNASSIGNED — the adopting organisation must assign a named owner before relying on this set (evidence doctor warns while unassigned).
> Last reviewed: never by an adopter; drafted 2026-09-24. **Not an authoritative interpretation.**

## Controls

| ID | Control | What to check in a change | Typical evidence |
| --- | --- | --- | --- |
| P11-01 | Validation — §11.10(a) | System change is covered by validation appropriate to its risk; the change's validation impact is assessed | Impact assessment, test evidence |
| P11-02 | Accurate copies — §11.10(b) | Records can be exported in human-readable and electronic form suitable for inspection | Export test, sample output |
| P11-03 | Record protection — §11.10(c) | Records remain retrievable and unaltered for the retention period, across migration, serialization or storage-class change | Migration test, hash/seal verification |
| P11-04 | Access limitation — §11.10(d) | Access to the system is limited to authorised individuals | Authn config, access review |
| P11-05 | Audit trail — §11.10(e) | Every create, modify and delete on a regulated record emits a secure, computer-generated, time-stamped audit entry with actor, action, entity, prior and new value. Entries do not obscure prior values and are retained as long as the record | Audit-event test, schema, retention config |
| P11-06 | Operational sequencing — §11.10(f) | Workflow steps cannot be performed out of order where sequencing matters | State-machine test |
| P11-07 | Authority checks — §11.10(g) | Only authorised individuals may use the system, sign, access, or perform the operation. Enforced server-side, per role and per tenant | Authorisation test per role |
| P11-08 | Device checks — §11.10(h) | Where the source of data entry matters, it is verified | Config, test |
| P11-09 | Training — §11.10(i) | Users have documented competence for the operations they perform | Training records (process control) |
| P11-10 | Accountability policy — §11.10(j) | Policy holds individuals accountable for actions under their signature | Policy document (process control) |
| P11-11 | Documentation control — §11.10(k) | System documentation is controlled and change-tracked | Version control, change records |
| P11-12 | Signature manifestation — §11.50 | Displayed and printed signatures carry printed name, date and time **with timezone**, and the meaning of the signing (author, reviewer, approver) | Rendering test, print/export test |
| P11-13 | Signature-record linking — §11.70 | A signature cannot be excised, copied, or transferred to another record | Tamper test, seal verification |
| P11-14 | Signature uniqueness — §11.100 | Each signature is unique to one individual, never reused or reassigned | Identity model, test |
| P11-15 | Two components — §11.200(a)(1) | Non-biometric signing uses two distinct identification components; both on first signing of a session, at least one on each subsequent signing in a continuous session | Signing flow test |
| P11-16 | Non-repudiation — §11.200(a)(2)(3) | Signatures are usable only by their genuine owner; attempted use by another requires collaboration of two or more individuals | Design review |
| P11-17 | Credential controls — §11.300 | Uniqueness of ID/password combinations, periodic revision, loss management, unauthorised-use detection and reporting | Authn config, alerting |

## ALCOA+ cross-check

Attributable, Legible, Contemporaneous, Original, Accurate — plus Complete, Consistent,
Enduring, Available. Run the change against each; it catches things the control list
misses because it asks about the record rather than the system.

## Blocking classes

Any **Not met** on P11-03, P11-05, P11-07, P11-12, P11-13 or P11-14 blocks the merge.
These are record integrity, audit trail, authority, and signature integrity — the ones a
customer cites in their own inspection.

## Common misses

- Audit events that fire but omit the **prior** value, so the trail shows what it became
  and not what it was.
- Batching or asynchronous audit writes that break contemporaneity under load.
- Timezone dropped in rendering or export, which passes every test done in one timezone.
- Authorisation enforced in the UI and not on the endpoint.
- Migration and storage-class changes treated as infrastructure work rather than as
  record-integrity changes.
