# PCI DSS — payment card data

> Scope: systems that store, process or transmit cardholder data, and systems connected
> to them. **Scope reduction is the primary control** — the cheapest way to satisfy this
> is to not handle card data. Source: drafted from public descriptions.
> Owner: UNASSIGNED — the adopting organisation must assign a named owner before relying on this set (evidence doctor warns while unassigned).
> Last reviewed: never by an adopter; drafted 2026-09-24. **Not an authoritative interpretation.**

## Controls

| ID | Control | What to check in a change | Typical evidence |
| --- | --- | --- | --- |
| PCI-01 | Scope | Does this change bring new systems into scope? Answer before anything else | Scope assessment |
| PCI-02 | No prohibited storage | Full track data, CVV and PIN blocks are never stored post-authorisation, including in logs, caches, backups and error payloads | Log review, storage review |
| PCI-03 | PAN protection | Primary account numbers rendered unreadable in storage; masked on display to the minimum needed | Encryption/tokenisation config |
| PCI-04 | Transmission encryption | Strong cryptography on open networks; no deprecated protocol versions | TLS config, scan |
| PCI-05 | Access by business need | Access restricted by role and business need to know; default-deny | Authorisation tests |
| PCI-06 | Unique IDs and strong authn | Individual identity for anyone with access; MFA where required | Identity config |
| PCI-07 | Secure development | Changes follow a documented process; common vulnerability classes addressed; code reviewed | PR record, scan reports |
| PCI-08 | Change control | Changes to in-scope systems are authorised, tested, and backed out cleanly | Change record |
| PCI-09 | Logging | Access to cardholder data and administrative actions are logged with actor, type, date, success, origin and affected data | Log schema |
| PCI-10 | Vulnerability management | Dependencies patched within the required window; scans clean | Scan reports |
| PCI-11 | Third parties | Service providers handling card data are assessed and their compliance status tracked | Vendor records |

## Blocking classes

Any **Not met** on PCI-02, PCI-03 or PCI-04. PCI-02 in particular: prohibited storage is
not a finding to schedule, it is a stop.

## Common misses

- Card data reaching **logs, APM traces or error-reporting services** — nearly always via
  a generic "log the request body" line added for debugging.
- A new integration quietly expanding scope to systems that were previously out of it.
- Masking applied in the UI while the API returns the full PAN.
