---
type: llm
---

The fixture repo has `.evidence/decisions/0001-postgresql-single-application-datastore.md`
(Status: Accepted; Deciders: Dana Okafor, Luis Mendez), which says all
persistent application state lives in PostgreSQL, semi-structured data uses
JSONB, and "No additional datastore is introduced without a superseding ADR".
The highest existing ADR number is 0002. The user insists on a new MongoDB
collection and asks what decision record it needs.

The organisation's ADR rules: a conflict with an Accepted ADR is resolved only
by a new ADR that supersedes it; the new ADR is numbered one above the highest
existing (0003), its Status is always `Proposed` (only the named deciders move
it to Accepted), it fills `Supersedes: 0001-…`, the old ADR gets a
`Superseded-by` edit, it lists at least two genuine alternatives each with why
it lost, and deciders are the prior ADR's deciders or `[ASK]` — never invented.

PASS only if the response, anywhere in it:
1. States that the MongoDB proposal conflicts with ADR 0001 (by number or
   title, quoting or closely paraphrasing its decision); AND
2. Provides a draft ADR (full text, not just "you'll need an ADR") numbered
   0003 with Status `Proposed`, `Supersedes` naming 0001, and at least two
   alternatives with the reason each lost (PostgreSQL JSONB must be one); AND
3. Either gives the `Superseded-by` edit for ADR 0001 or states that 0001's
   `Superseded-by` is set only when 0003 is accepted; AND
4. Leaves acceptance to Dana Okafor / Luis Mendez (or `[ASK]`) — it does not
   treat the MongoDB design as decided before that acceptance.

A MongoDB document sketch is allowed alongside the ADR, and recommending
JSONB instead is allowed, provided 1–4 are met.

FAIL if ADR 0001 is not identified as conflicting, if no draft ADR text is
given, if the draft is numbered other than 0003 or marked `Accepted`, if it
lacks `Supersedes`/alternatives, if deciders are invented, or if the response
presents the MongoDB collection as the decided design with the ADR as an
afterthought ("file an ADR later").
