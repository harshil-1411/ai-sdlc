#!/bin/bash
set -euo pipefail

mkdir -p .github/workflows
cat > .github/workflows/ci.yml <<'EOF'
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test
EOF

cat > README.md <<'EOF'
# Fixture App
Issues tracked in Jira, project key FIX: https://fixture.atlassian.net/browse/FIX
EOF
