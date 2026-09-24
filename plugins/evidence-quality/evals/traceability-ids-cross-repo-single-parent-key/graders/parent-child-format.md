---
type: llm
---

The traceability-ids skill's cross-repository rules go beyond "use a parent
ticket": each repo carries `PARENT/CHILD`; requirement IDs are allocated once
against the parent; the parent issue records which repositories participate,
and a participating repo with no linked child chain is an incomplete change
(a release finding, like `NO COVERAGE`); and the integration test that proves
the cross-repo behaviour lives in ONE named repository declared on the parent
— "both sides tested their half" is not proof the whole works.

PASS only if the response, anywhere in the reply (judge substance, not length,
hedging or placement — flagging that `.evidence/context/toolchain.md` is
missing or that the concrete child keys aren't known yet is fine):
- says each repository's branch/commits/PR carry both the parent key and its
  own child key, written as `PLAT-100/<CHILD>`;
- says the requirement ID is allocated once against the parent and referenced,
  not re-numbered, from the second repository;
- says the integration test exercising the crossing between the two repos is
  owned by one named repository, declared on the parent issue (not "each
  repo tests its half"); and
- says the parent issue records the participating repositories, and/or that
  a participating repo without a linked child chain is an incomplete change /
  release finding.

FAIL if the response has each repo invent its own requirement ID, never names
the `PARENT/CHILD` format, lets either repo use only its own key, relies on
each repo testing its own half as proof of the cross-repo requirement, or
omits both the participating-repos record and the missing-child-chain rule.
Presenting invented child keys as the real keys to use (rather than as
examples or `[ASK]`) is also a FAIL.
