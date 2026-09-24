---
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
tags: [non-trigger, toolchain-discovery]
---

Can you refactor this function to use async/await instead of callbacks?

```js
function loadUser(id, cb) {
  db.query('SELECT * FROM users WHERE id = ?', [id], (err, row) => cb(err, row));
}
```
