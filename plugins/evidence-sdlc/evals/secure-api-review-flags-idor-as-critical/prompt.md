---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [behavior, secure-api-review]
---

Here's the handler for `GET /api/invoices/:id`:

```
app.get('/api/invoices/:id', requireAuth, async (req, res) => {
  const invoice = await db.invoices.findById(req.params.id);
  res.json(invoice);
});
```

`requireAuth` just checks that the request has a valid JWT for some user; it
doesn't check anything about the invoice itself. Review this.
