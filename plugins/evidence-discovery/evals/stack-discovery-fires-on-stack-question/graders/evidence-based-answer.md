---
type: llm
---

The fixture declares `express`, `pg` and `mongoose` in `package.json`, but only
`express` (`src/server.js`) and `pg` (`src/db/pool.js`) are actually imported.
`mongoose` is declared and never used. stack-discovery's Rule 3 says a declared
dependency is not proof of use and both must be recorded; Rule 4 says every
entry carries a `[confirmed]`, `[inferred]` or `[ASK]` marker; and the output is
the profile `.evidence/context/stack.md`.

PASS only if the response does all of the following, anywhere in the reply:
1. Names Node.js/JavaScript, Express and PostgreSQL (via `pg`), citing at least
   one file it read for each (e.g. `package.json`, `src/server.js`,
   `src/db/pool.js`).
2. Treats `mongoose`/MongoDB as declared but with no evidence of use (no import
   found). It must not list MongoDB as part of the stack in use. Calling it
   dead or unused, or marking it `[ASK]`/`[inferred]` with that reason, all
   count.
3. Tags its stack claims with the literal confidence markers `[confirmed]`,
   `[inferred]` and/or `[ASK]`. At least the Express and PostgreSQL claims must
   carry one. Hedging words such as "likely" or "confirmed by" in prose do not
   count as markers.
4. Names `.evidence/context/stack.md` as the profile it wrote, would write, or
   proposes to write. Saying it could not write the file in this session is
   fine.

FAIL if any one of the four is missing. That includes: MongoDB presented as a
datastore in use; no literal confidence markers; or no mention of
`.evidence/context/stack.md`. Also FAIL if the response names a framework or
datastore not evidenced in the fixture files.
