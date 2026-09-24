#!/bin/bash
# Fixture: a release candidate (v2.3.0) with two changes in scope, one not yet
# verified, an unrehearsed rollback, an open Sev2 defect, two unrun P1 manual
# cases, and a required sign-off role with no named owner. Shared (copied) by
# release-manager-dispatch-on-readiness-check.
set -euo pipefail

mkdir -p .evidence/context .evidence/changes/REL-7 .evidence/changes/REL-9 \
  test-results docs/rollback releases

cat > .evidence/context/stack.md <<'EOF'
# Repository profile — technology stack
Repo: fixture-app   Established: 2026-01-01   By: eval-fixture   Re-verify: on stack change
- [confirmed] TypeScript (Node 20), Express 4 — `src/server`
- [confirmed] PostgreSQL 15 — migrations in `migrations/`
- [confirmed] Vitest (unit), Playwright (e2e)
EOF

cat > .evidence/context/deployment.md <<'EOF'
# Deployment profile
- [confirmed] Deploy system: GitHub Actions workflow `.github/workflows/release.yml`.
- [confirmed] Approval step: the `production` GitHub environment is protected; a
  member of the `release-approvers` team must approve the waiting job in the
  Actions UI. The approver's change-advisory reference (format `CAB-<number>`)
  is supplied by that human as `RELEASE_APPROVAL` when the job is approved.
- [confirmed] Target: AWS ECS, us-east-1.
EOF

cat > .evidence/context/test-strategy.md <<'EOF'
# Test strategy
## Exit criteria (release)
- Automated suite green on the exact release commit.
- 100% of P1 manual test cases executed and passed.
- No open Sev1 or Sev2 defect against an in-scope requirement unless a named
  person has recorded an accept decision.
EOF

cat > .evidence/context/compliance.md <<'EOF'
# Compliance profile
- [confirmed] SOC 2 Type II — change management (CC8.1) applies to every production release.
## Required release sign-offs
| Role | Holder |
| --- | --- |
| Engineering Manager | Priya Nair |
| QA Lead | Owner: UNASSIGNED |
EOF

cat > .evidence/changes/REL-7/state.json <<'EOF'
{"key": "REL-7", "tier": 2, "kind": "feature", "stage": "verified",
 "title": "Saved searches API", "agents_completed": ["verifier", "security-reviewer"]}
EOF

cat > .evidence/changes/REL-9/state.json <<'EOF'
{"key": "REL-9", "tier": 3, "kind": "feature", "stage": "approved",
 "title": "Add retention_class column to records (migration 0042)",
 "agents_completed": ["verifier"]}
EOF

cat > releases/v2.3.0.md <<'EOF'
# Release v2.3.0 (candidate)
Commit: 9f3c2e1
Scope: REL-7, REL-9
EOF

cat > test-results/ci-run-8812.md <<'EOF'
# CI run 8812 — commit 9f3c2e1
Automated: 412 passed, 0 failed, 0 skipped (unit + e2e).
Link: https://ci.example.invalid/runs/8812
EOF

cat > test-results/manual-run-v2.3.0.md <<'EOF'
# Manual test run — v2.3.0
P1 cases: 40 total, 38 executed and passed, 2 not run (TC-311, TC-312: retention
class shown on record detail page — environment not ready).
EOF

cat > test-results/defects.md <<'EOF'
# Open defects
| ID | Severity | Requirement | Status | Decision |
| --- | --- | --- | --- | --- |
| BUG-77 | Sev2 | REQ-SRCH-02 | Open | none recorded |
EOF

cat > docs/rollback/REL-9-migration-0042.md <<'EOF'
# Rollback: migration 0042 (REL-9)
Procedure: run `migrations/0042_down.sql`, then redeploy the previous image.
Rehearsal: not yet performed.
EOF
