#!/bin/bash
set -euo pipefail

mkdir -p .evidence/context
cat > .evidence/context/compliance.md <<'EOF'
# Repository profile — industry and regulatory context
Project: fixture-app   Established: 2026-01-01   Confirmed by: eval-fixture, Security   Re-verify: annually

## Applicable frameworks

| Framework | Role | Control set to load | Named owner | Audited by / when | Confidence |
| --- | --- | --- | --- | --- | --- |
| SOC 2 Type II | certification held | `references/soc2.md` | Security | ExampleAudit LLC / 2026-06 | [confirmed] |

## Evidence profile
- [confirmed] evidence_profile: L1, raised to L2 for Tier 2+ and L3 for Tier 3

## Regulated record types for this product
- [confirmed] None beyond standard access/audit logging — internal tooling is not customer-facing

## Customer reliance
- [confirmed] Do customers cite our controls in their own audits or validation? yes
- [confirmed] If yes: which controls, and what changes trigger customer notification: access control and audit logging controls only
EOF
