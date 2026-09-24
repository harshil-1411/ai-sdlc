#!/bin/bash
set -euo pipefail

mkdir -p .evidence/context
cat > .evidence/context/toolchain.md <<'EOF'
# Toolchain profile

## Issue tracker
- [confirmed] Jira, project key FIX

## Test management
- [confirmed] TestRail, project "Fixture App", suite "Regression"
- [confirmed] Template in use: "Test Case (Steps)"
- [confirmed] Required custom fields: `custom_tracker_key` (string), `custom_automation_status` (enum: Automated / Manual / To Automate)
- [confirmed] Field carrying the tracker key: `custom_tracker_key`
- [confirmed] Write access: this session MAY write new test cases via the TestRail connector; write decision recorded 2026-01-01
EOF
