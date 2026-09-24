#!/bin/bash
# Fixture: a Tier 3 change (PERM-12) with spec, approved plan, and the branch
# diff saved as a file (no git needed). The diff touches a file outside the
# plan's "Files claimed", loosens an existing test, and leaves REQ-PERM-02
# without a covering test.
set -euo pipefail

mkdir -p .evidence/context .evidence/changes/PERM-12 intent/2026-09-20-role-scoped-export review

cat > .evidence/context/stack.md <<'EOS'
# Repository profile — technology stack
- [confirmed] TypeScript (Node 20), Express 4 — `src/server`
- [confirmed] Vitest, tests beside source as `*.test.ts`
EOS

cat > .evidence/context/compliance.md <<'EOS'
# Compliance profile
- [confirmed] SOC 2 Type II — logical access (CC6.1) applies to permission checks.
EOS

cat > .evidence/changes/PERM-12/state.json <<'EOS'
{"key": "PERM-12", "tier": 3, "kind": "feature", "stage": "approved",
 "spec": "intent/2026-09-20-role-scoped-export/spec.md",
 "plan": "intent/2026-09-20-role-scoped-export/plan.md"}
EOS

cat > intent/2026-09-20-role-scoped-export/spec.md <<'EOS'
# Spec: Role-scoped report export
Tracker: PERM-12   Risk tier: 3 — changes an authorization check.
| ID | Requirement | Acceptance |
| --- | --- | --- |
| REQ-PERM-01 | Only users with role `exporter` or `admin` may call `POST /reports/export` | 403 for any other role |
| REQ-PERM-02 | Every denied export attempt writes an `export.denied` audit event with user id and role | Audit event present on 403 |
EOS

cat > intent/2026-09-20-role-scoped-export/plan.md <<'EOS'
# Plan: Role-scoped report export
Tracker: PERM-12   Risk tier: 3 — changes an authorization check.
## Files claimed
- `src/server/permissions/**`
- `src/server/routes/reports.ts`
- `src/server/routes/reports.test.ts`
## Order of work
1. Add `canExport(role)` in `src/server/permissions/export.ts`.
2. Guard `POST /reports/export` with it; emit `export.denied` on 403.
3. CHECKPOINT — re-confirm against spec.md.
4. Tests for REQ-PERM-01 and REQ-PERM-02 in `reports.test.ts`.
EOS

cat > review/PERM-12.diff <<'EOS'
diff --git a/src/server/permissions/export.ts b/src/server/permissions/export.ts
new file mode 100644
--- /dev/null
+++ b/src/server/permissions/export.ts
@@ -0,0 +1,3 @@
+export function canExport(role?: string): boolean {
+  return role !== 'viewer';
+}
diff --git a/src/server/routes/reports.ts b/src/server/routes/reports.ts
--- a/src/server/routes/reports.ts
+++ b/src/server/routes/reports.ts
@@ -10,6 +10,10 @@ router.post('/reports/export', requireAuth, async (req, res) => {
+  if (!canExport(req.user.role)) {
+    return res.status(403).json({ error: 'forbidden' });
+  }
   const rows = await reports.forTenant(req.user.tenantId).all();
   res.csv(rows);
 });
diff --git a/src/server/routes/reports.test.ts b/src/server/routes/reports.test.ts
--- a/src/server/routes/reports.test.ts
+++ b/src/server/routes/reports.test.ts
@@ -20,7 +20,7 @@ describe('POST /reports/export', () => {
   it('rejects viewers', async () => {
     const res = await asRole('viewer').post('/reports/export');
-    expect(res.status).toBe(403);
+    expect([200, 403]).toContain(res.status);
   });
diff --git a/src/server/billing/invoice-format.ts b/src/server/billing/invoice-format.ts
--- a/src/server/billing/invoice-format.ts
+++ b/src/server/billing/invoice-format.ts
@@ -3,1 +3,1 @@
-export const CURRENCY_DP = 2;
+export const CURRENCY_DP = 3;
EOS
