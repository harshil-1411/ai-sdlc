#!/bin/bash
set -euo pipefail

mkdir -p .evidence/context intent/2026-01-01-mfa-recovery

cat > .evidence/context/compliance.md <<'EOF'
# Repository profile — industry and regulatory context
Project: fixture-app   Established: 2026-01-01   Confirmed by: eval-fixture, Security   Re-verify: annually

## Applicable frameworks

| Framework | Role | Control set to load | Named owner | Audited by / when | Confidence |
| --- | --- | --- | --- | --- | --- |
| SOC 2 Type II | certification held | `references/soc2.md` | Security | ExampleAudit LLC / 2026-06 | [confirmed] |

## Evidence profile
> No evidence_profile recorded yet for this project.
EOF

cat > intent/2026-01-01-mfa-recovery/intent.md <<'EOF'
# Intent: Self-service MFA device recovery
Tracker: FIX-101   Author: eval-fixture, Support   Date: 2026-01-01   Status: accepted

## Problem
Customers who lose their MFA device must call support and wait up to two days
for a manual reset.

## Regulated record impact
Yes — authentication events are part of the audit trail.
EOF

cat > intent/2026-01-01-mfa-recovery/spec.md <<'EOF'
# Spec: Self-service MFA device recovery
Tracker: FIX-101   From: intent/2026-01-01-mfa-recovery/intent.md   Risk tier: 3

## Requirements
| ID | Requirement | Source (intent.md section) | Acceptance |
| --- | --- | --- | --- |
| REQ-AUTH-01 | Customer can request a recovery link via verified email | Problem | Link sent, single use, expires in 15 min |
EOF

cat > intent/2026-01-01-mfa-recovery/plan.md <<'EOF'
# Plan: Self-service MFA device recovery
Tracker: FIX-101   From: spec.md   Approved by: eval-fixture-engineer   Date: 2026-01-02

## Proof
| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| REQ-AUTH-01 | API | Yes | TC-501 | auth.recovery.test.ts | CI run #4821 |
EOF
