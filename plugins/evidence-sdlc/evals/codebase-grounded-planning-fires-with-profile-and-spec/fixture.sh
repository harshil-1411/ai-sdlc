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
- [confirmed] Express 4 — `src/server/app.ts`, routes in `src/server/routes/`
- [confirmed] React 18 with Vite — `src/client`

## Data and persistence
- [confirmed] PostgreSQL 15 — `src/server/db`, migrations in `migrations/`

## Testing
- [confirmed] Vitest for unit tests, Playwright for e2e, tests live beside source as `*.test.ts`
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

mkdir -p src/server/routes src/server/auth src/server/db src/client migrations .github/workflows

cat > src/server/app.ts <<'EOF'
// existing Express app entry point
import { authRouter } from './routes/auth';
export const app = { use() {} };
app.use('/auth', authRouter);
EOF
cat > src/server/routes/auth.ts <<'EOF'
// existing auth routes: login, logout, refresh
export const authRouter = {};
EOF
cat > src/server/routes/auth.test.ts <<'EOF'
// existing tests for the auth routes
EOF
cat > src/server/auth/mfa.ts <<'EOF'
// existing MFA verification logic
export function verifyMfaCode() {}
EOF
cat > src/server/db/index.ts <<'EOF'
// existing PostgreSQL connection pool
export const db = {};
EOF
cat > migrations/0001_init.sql <<'EOF'
-- existing baseline migration
CREATE TABLE users (id uuid PRIMARY KEY, full_name text);
EOF
cat > src/client/App.tsx <<'EOF'
// existing React entry point
export function App() { return null; }
EOF
cat > .github/workflows/ci.yml <<'EOF'
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "existing CI pipeline"
EOF

mkdir -p intent/2026-01-01-mfa-recovery
cat > intent/2026-01-01-mfa-recovery/intent.md <<'EOF'
# Intent: Self-service MFA device recovery
Tracker: FIX-101   Author: eval-fixture, Support   Date: 2026-01-01   Status: accepted

## Problem
Customers who lose their MFA device must call support and wait up to two days
for a manual reset.

## Proposed outcome
A customer can recover MFA access via a verified backup channel without a
support call, in under 10 minutes.
EOF

cat > intent/2026-01-01-mfa-recovery/spec.md <<'EOF'
# Spec: Self-service MFA device recovery
Tracker: FIX-101   From: intent/2026-01-01-mfa-recovery/intent.md   Risk tier: 3

## Requirements
| ID | Requirement | Source (intent.md section) | Acceptance |
| --- | --- | --- | --- |
| REQ-AUTH-01 | Customer can request a recovery link via verified email | Problem | Link sent, single use, expires in 15 min |
| REQ-AUTH-02 | Recovery event is written to the audit trail | Regulated record impact | Audit event present with actor, timestamp, outcome |

## Design
Extend `src/server/routes/auth.ts` with a new recovery endpoint. Extend
`src/server/auth/mfa.ts` with a `startRecovery`/`completeRecovery` pair rather
than adding a parallel MFA module.

## Areas of concern
Whether the 10-minute window is acceptable to Security — routed to Security.
EOF
