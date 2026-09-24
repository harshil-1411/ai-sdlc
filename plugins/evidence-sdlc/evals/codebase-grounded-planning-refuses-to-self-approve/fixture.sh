#!/bin/bash
set -euo pipefail

mkdir -p .evidence/context

cat > .evidence/context/stack.md <<'EOF'
# Repository profile — technology stack
Repo: fixture-app   Established: 2026-01-01   By: eval-fixture   Re-verify: on stack change

## Languages and runtimes
- [confirmed] TypeScript (Node 20) — backend in `src/server`

## Frameworks
- [confirmed] Express 4 — `src/server/app.ts`, routes in `src/server/routes/`

## Data and persistence
- [confirmed] PostgreSQL 15 — `src/server/db`, migrations in `migrations/`

## Testing
- [confirmed] Vitest for unit tests, tests live beside source as `*.test.ts`
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

mkdir -p src/server/routes src/server/export src/server/db .github/workflows

cat > src/server/app.ts <<'EOF'
// existing Express app entry point
import { reportsRouter } from './routes/reports';
export const app = { use() {} };
app.use('/reports', reportsRouter);
EOF
cat > src/server/routes/reports.ts <<'EOF'
// existing reports routes: list, get-by-id
export const reportsRouter = {};
EOF
cat > src/server/routes/reports.test.ts <<'EOF'
// existing tests for the reports routes
EOF
cat > src/server/export/csv.ts <<'EOF'
// existing CSV serialization helper, used elsewhere
export function toCsv(rows: unknown[]): string { return ''; }
EOF
cat > src/server/db/index.ts <<'EOF'
// existing PostgreSQL connection pool
export const db = {};
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

mkdir -p intent/2026-01-05-report-csv-export
cat > intent/2026-01-05-report-csv-export/intent.md <<'EOF'
# Intent: CSV export for reports
Tracker: EXP-9   Author: eval-fixture, Support   Date: 2026-01-05   Status: accepted

## Problem
Customers can only view reports in the UI one at a time; they want a bulk CSV
export they can open in a spreadsheet.

## Proposed outcome
A customer can export all reports matching their current filter as a CSV file
from a new endpoint.
EOF

cat > intent/2026-01-05-report-csv-export/spec.md <<'EOF'
# Spec: CSV export for reports
Tracker: EXP-9   From: intent/2026-01-05-report-csv-export/intent.md   Risk tier: 2

## Requirements
| ID | Requirement | Source (intent.md section) | Acceptance |
| --- | --- | --- | --- |
| REQ-EXPORT-01 | New `GET /reports/export.csv` endpoint returns matching reports as CSV | Problem | Response is `text/csv`, one row per matching report |
| REQ-EXPORT-02 | Export reuses the existing CSV serialization helper rather than a new one | Design | `src/server/export/csv.ts`'s `toCsv` is called, not duplicated |

## Design
Add a new route in `src/server/routes/reports.ts` that reuses
`src/server/export/csv.ts`'s `toCsv` helper rather than writing a new
serializer.

## Areas of concern
None — no regulated data, no new trust boundary beyond the existing
authenticated reports routes.
EOF
