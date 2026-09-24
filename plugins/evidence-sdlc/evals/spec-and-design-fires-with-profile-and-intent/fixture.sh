#!/bin/bash
set -euo pipefail

mkdir -p .evidence/context

cat > .evidence/context/stack.md <<'EOF'
# Repository profile — technology stack
Repo: fixture-app   Established: 2026-01-01   By: eval-fixture   Re-verify: on stack change

## Languages and runtimes
- [confirmed] TypeScript (Node 20) — backend in `src/server`
- [confirmed] TypeScript (React 18) — frontend in `src/client`

## Frameworks
- [confirmed] Express 4 — `src/server/app.ts`
- [confirmed] React 18 with Vite — `src/client`

## Data and persistence
- [confirmed] PostgreSQL 15 — `src/server/db`, migrations in `migrations/`

## Testing
- [confirmed] Vitest for unit tests, Playwright for e2e
EOF

cat > .evidence/context/deployment.md <<'EOF'
# Deployment profile
- [confirmed] Deployed to AWS ECS, one region: us-east-1
- [confirmed] CI: GitHub Actions, `.github/workflows/ci.yml`
EOF

cat > .evidence/context/design-system.md <<'EOF'
# Design system
- [confirmed] Component library: internal `@fixture/ui` package, Storybook-documented
EOF

cat > .evidence/context/toolchain.md <<'EOF'
# Toolchain
- [confirmed] Issue tracker: Jira, project key FIX
- [confirmed] Test management: TestRail
EOF

cat > .evidence/context/compliance.md <<'EOF'
# Compliance profile
- [confirmed] No regulated frameworks apply to this fixture app (internal tool, no PII, no financial or health records).
EOF

mkdir -p intent/2026-01-01-mfa-recovery
cat > intent/2026-01-01-mfa-recovery/intent.md <<'EOF'
# Intent: Self-service MFA device recovery

Tracker: FIX-101   Author: eval-fixture, Support   Date: 2026-01-01   Status: accepted

## Problem
Customers who lose their MFA device must call support and wait up to two days
for a manual reset. Affects all authenticated customers.

## Proposed outcome
A customer can recover MFA access via a verified backup channel (email +
one-time link) without a support call, in under 10 minutes.

## Affected users and systems
Customer-facing auth flow, support team, the auth service.

## Regulated record impact
Yes — authentication events are part of the audit trail.

## Compliance evidence impact
Unknown — routed to Security/QA-RA to confirm.

## Data classification
Authentication credentials, contact information (email).

## Constraints
Must not weaken existing MFA guarantees for accounts that do not use recovery.

## Out of scope
Recovery via SMS; account recovery when the customer also lost email access.

## Open questions
- Is a 10-minute recovery window acceptable to Security? — Security
EOF
