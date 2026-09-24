---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill, Agent]
tags: [behavior, agent, security-reviewer]
---

Run the security reviewer over this PR diff before I open it. `loadTenant` lives in
`src/middleware/tenant.ts`, which isn't part of this PR and which I can't
share right now; our ORM (Sequelize) is configured with default options.

```diff
+router.get('/api/records/:id', requireAuth, loadTenant, async (req, res) => {
+  const record = await Record.findOne({
+    where: { id: req.params.id, tenantId: req.tenant?.id },
+  });
+  if (!record) return res.status(404).end();
+  res.json(record);
+});
```

We only care about real problems — please don't pad the review with maybes.
