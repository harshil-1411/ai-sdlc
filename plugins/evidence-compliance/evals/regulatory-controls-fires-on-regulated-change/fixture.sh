#!/bin/bash
set -euo pipefail

mkdir -p .evidence/context
cat > .evidence/context/compliance.md <<'EOF'
# Repository profile — industry and regulatory context
Project: fixture-app   Established: 2026-01-01   Confirmed by: eval-fixture, Security   Re-verify: annually

## Industry and markets
- [confirmed] industry: B2B SaaS, workflow automation
- [confirmed] market segments served: mid-market and enterprise
- [confirmed] jurisdictions — customers: US, EU
- [confirmed] jurisdictions — data storage and processing: US (us-east-1)

## Applicable frameworks

| Framework | Role | Control set to load | Named owner | Audited by / when | Confidence |
| --- | --- | --- | --- | --- | --- |
| SOC 2 Type II | certification held | `references/soc2.md` | Security | ExampleAudit LLC / 2026-06 | [confirmed] |

## Explicitly out of scope
| Framework | Why it does not apply | Confirmed by |
| --- | --- | --- |
| HIPAA | Product does not handle protected health information | Security |

## Evidence profile
- [confirmed] evidence_profile: L1, raised to L2 for Tier 2+ and L3 for Tier 3

## Regulated record types for this product
- [confirmed] Admin role-change events: cited by customers in their own SOC 2 vendor reviews

## Customer reliance
- [confirmed] Do customers cite our controls in their own audits or validation? yes
- [confirmed] If yes: which controls, and what changes trigger customer notification: access control and audit logging controls; any change to how roles are authorised triggers notification to enterprise customers under contract

## Sensitive data classes handled
| Class | Where stored | Residency constraint | Framework driving the constraint |
| --- | --- | --- | --- |
| Authentication role/session data | `sessions` table, Postgres | US only | SOC 2 |

## Existing certifications, validations and audit history
| Item | Status | Last assessed | Next due |
| --- | --- | --- | --- |
| SOC 2 Type II | Certified | 2026-06 | 2027-06 |
EOF
