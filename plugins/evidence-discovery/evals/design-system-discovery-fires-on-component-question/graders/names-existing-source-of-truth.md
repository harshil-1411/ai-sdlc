---
type: llm
---

The fixture depends on the internal design-system package `@fixture/ui`
(`package.json`), with Storybook docs noted in `src/components/README.md` and
tokens in `tokens.json`. design-system-discovery requires:
- the survey result is recorded in `.evidence/context/design-system.md`;
- "extend before you add": a new component needs a written justification in
  `plan.md` that names the existing components considered and why each was
  insufficient.

PASS only if the response does all of the following, anywhere in the reply:
1. Names `@fixture/ui` as the existing design-system source of truth to extend.
   It must not recommend a different library or a hand-rolled modal. Honest
   caveats are fine, e.g. that it cannot confirm `@fixture/ui` ships a Dialog
   component.
2. States the extend-before-add rule in substance: use or extend an existing
   `@fixture/ui` component. If a new modal component is genuinely needed, a
   written justification is required that names the existing components
   considered and why each fell short. It counts wherever that justification
   is said to live (`plan.md`, the plan, a PR description), as long as the
   written, named-alternatives justification is stated as a requirement.
3. Names `.evidence/context/design-system.md` as the profile it wrote, would
   write, or proposes to write. Saying it could not write the file in this
   session is fine.

FAIL if `@fixture/ui` is not named as the thing to extend; if the response
never says a new component requires a written justification naming the
alternatives considered; or if `.evidence/context/design-system.md` is never
mentioned. Judge substance, not placement or length.
