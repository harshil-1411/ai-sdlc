---
type: llm
---

PASS if the response names Node.js/Express and PostgreSQL, cites the actual
files it read (`package.json`, `src/server.js`, `src/db/pool.js`) as evidence,
and marks its claims with a confidence indicator such as `[confirmed]` — not a
guess and not sourced from documentation that doesn't exist in this fixture.

FAIL if the response names a framework or datastore not evidenced in the
fixture files, or answers without citing any file it read.
