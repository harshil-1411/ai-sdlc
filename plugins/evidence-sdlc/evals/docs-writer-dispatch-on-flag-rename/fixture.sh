#!/bin/bash
# Fixture: CLI-22 (merged) renamed `--timeout` (seconds) to `--timeout-ms`
# (milliseconds) in the CLI source. Docs still describe the old flag in three
# places, one of them easy to miss (docs/guides/ci.md).
set -euo pipefail

mkdir -p src/cli docs/guides intent/2026-09-18-timeout-ms

cat > src/cli/options.ts <<'EOS'
// CLI options. CLI-22: `--timeout` (seconds) replaced by `--timeout-ms` (milliseconds).
export const options = {
  '--timeout-ms': { type: 'number', default: 30000, help: 'Request timeout in milliseconds' },
  '--retries': { type: 'number', default: 2, help: 'Retry count' },
};
EOS

cat > intent/2026-09-18-timeout-ms/spec.md <<'EOS'
# Spec: millisecond timeouts
Tracker: CLI-22   Risk tier: 2 — changes a public CLI flag.
| ID | Requirement |
| --- | --- |
| REQ-CLI-01 | `--timeout` is removed; `--timeout-ms <n>` sets the request timeout in milliseconds, default 30000 |
EOS

cat > README.md <<'EOS'
# fetchr

Fetch many URLs in parallel.

## Usage

    fetchr urls.txt --timeout 30 --retries 2

| Flag | Default | Meaning |
| --- | --- | --- |
| `--timeout` | 30 | Request timeout in seconds |
| `--retries` | 2 | Retry count |
EOS

cat > docs/guides/ci.md <<'EOS'
# Running fetchr in CI

Slow runners need a longer timeout:

    fetchr urls.txt --timeout 120
EOS

cat > CHANGELOG.md <<'EOS'
# Changelog

## Unreleased

## 1.4.0
- CLI-17: add `--retries`.
EOS
