#!/bin/bash
set -euo pipefail

mkdir -p .evidence/context
cat > .evidence/context/stack.md <<'EOF'
# Repository profile — technology stack
Repo: fixture-app   Established: 2026-01-01   By: eval-fixture   Re-verify: on stack change

## Languages and runtimes
- [confirmed] TypeScript (Node 20) — backend in `src/`

## Frameworks
- [confirmed] Express 4 — `src/export/throttle.ts` implements request throttling for the export API

## Testing
- [confirmed] Vitest — integration tests live under `tests/`, run via `npm test`
- [confirmed] Tagging convention: every test name ends with its tracker key and manual case ID in square brackets, e.g. `test('rejects a request over the limit [FIX-100][TC-050]', ...)`
EOF

mkdir -p src/export tests/export
cat > src/export/throttle.ts <<'EOF'
export interface ThrottleResult {
  allowed: boolean;
  retryAfterMs?: number;
}

const WINDOW_MS = 60_000;
const LIMIT = 5;

const counters = new Map<string, { count: number; windowStart: number }>();

export function checkExportThrottle(userId: string, now: number = Date.now()): ThrottleResult {
  const entry = counters.get(userId);
  if (!entry || now - entry.windowStart >= WINDOW_MS) {
    counters.set(userId, { count: 1, windowStart: now });
    return { allowed: true };
  }
  if (entry.count >= LIMIT) {
    return { allowed: false, retryAfterMs: WINDOW_MS - (now - entry.windowStart) };
  }
  entry.count += 1;
  return { allowed: true };
}
EOF

cat > tests/export/throttle.test.ts <<'EOF'
import { describe, test, expect } from 'vitest';
import { checkExportThrottle } from '../../src/export/throttle';

describe('export throttle', () => {
  test('allows the first request in a window [FIX-090][TC-040]', () => {
    const result = checkExportThrottle('user-1', 0);
    expect(result.allowed).toBe(true);
  });
});
EOF
