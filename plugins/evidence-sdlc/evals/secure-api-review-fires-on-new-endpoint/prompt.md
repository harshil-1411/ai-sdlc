---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [trigger, secure-api-review]
---

I added a new endpoint before opening the PR, can you review it?

```js
app.get('/api/invoices/:id', requireAuth, async (req, res) => {
  try {
    const invoice = await db.invoices.findOne({
      where: { id: req.params.id, tenantId: req.user.tenantId },
    });
    if (!invoice) return res.status(404).json({ error: 'not found' });
    res.json(invoice);
  } catch (err) {
    res.status(500).json({ error: err.message, stack: err.stack });
  }
});
```
