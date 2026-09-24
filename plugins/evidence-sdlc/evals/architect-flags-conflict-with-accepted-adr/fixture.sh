#!/bin/bash
# Fixture: a repo with a stack profile and two Accepted ADRs. ADR 0001 makes
# PostgreSQL the only application datastore; the prompt proposes MongoDB.
set -euo pipefail

mkdir -p .evidence/context .evidence/decisions src/server/db migrations

cat > .evidence/context/stack.md <<'EOS'
# Repository profile — technology stack
Repo: fixture-app   Established: 2026-01-01   By: eval-fixture   Re-verify: on stack change
- [confirmed] TypeScript (Node 20), Express 4 — `src/server`
- [confirmed] PostgreSQL 15 (with JSONB in use) — `src/server/db`, migrations in `migrations/`
- [confirmed] Vitest for unit tests
EOS

cat > .evidence/context/deployment.md <<'EOS'
# Deployment profile
- [confirmed] AWS ECS, us-east-1; RDS PostgreSQL 15. No other managed datastore provisioned.
EOS

cat > .evidence/context/compliance.md <<'EOS'
# Compliance profile
- [confirmed] SOC 2 Type II. Backups, encryption at rest and access review are
  evidenced for the RDS PostgreSQL instance only.
EOS

cat > .evidence/decisions/0001-postgresql-single-application-datastore.md <<'EOS'
# 0001. Keep PostgreSQL as the single application datastore

Status: Accepted
Date: 2025-06-02
Deciders: Dana Okafor (Principal Engineer), Luis Mendez (Head of Platform)
Tracker: PLAT-12   Spec: intent/2025-06-01-datastore/spec.md
Supersedes: none
Superseded-by:

## Context
Two datastores doubled our backup, encryption and access-review evidence for SOC 2.

## Decision
All persistent application state lives in PostgreSQL. Semi-structured data uses
JSONB columns. No additional datastore is introduced without a superseding ADR.

## Consequences
One backup/restore path and one set of SOC 2 evidence. Document-shaped data must
be modelled as JSONB. Review trigger: a workload PostgreSQL demonstrably cannot serve.

## Alternatives
| Option | Why it lost |
| --- | --- |
| PostgreSQL + MongoDB for document data | Second evidence surface for SOC 2; two restore paths |
| DynamoDB for high-write tables | No workload needed it; vendor lock-in |
EOS

cat > .evidence/decisions/0002-uuid-primary-keys.md <<'EOS'
# 0002. Use UUIDv7 primary keys for new tables

Status: Accepted
Date: 2025-09-14
Deciders: Dana Okafor (Principal Engineer)
Tracker: PLAT-30   Spec: intent/2025-09-10-ids/spec.md
Supersedes: none
Superseded-by:

## Context
Sequential integer IDs leaked record counts to customers.

## Decision
Every new table uses a UUIDv7 primary key.

## Consequences
Existing tables keep integer keys until migrated.

## Alternatives
| Option | Why it lost |
| --- | --- |
| Keep bigserial | Enumeration of record counts |
| UUIDv4 | Poor index locality |
EOS

cat > src/server/db/index.ts <<'EOS'
// existing PostgreSQL pool (pg)
export const pool = {};
EOS
