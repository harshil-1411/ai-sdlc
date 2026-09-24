# evidence-discovery eval suite

19 cases covering all 6 skills: `stack-discovery`, `toolchain-discovery`,
`design-system-discovery`, `compliance-discovery`, `document-ingestion`,
`test-strategy-discovery`. Each
skill has a `trigger` case, a `non-trigger` case, and at least one `behavior`
case that checks the skill's actual non-obvious rule — not just that it fired.

Behavior cases worth noting:
- `stack-discovery-favors-code-over-docs` / `-flags-ambiguous-stack-as-ask` —
  Rule 0 ("documentation is a claim, not evidence") and Rule 1 ("never guess")
  from `stack-discovery/SKILL.md`.
- `toolchain-discovery-flags-community-mcp-risk` — the community-MCP
  supply-chain decision in Step 3.
- `design-system-discovery-flags-duplicate-libraries-as-ask` — the "two
  component libraries present" ambiguity rule.
- `compliance-discovery-pushes-back-on-casual-none-apply` — "the 'none apply'
  case is a real answer" but only when recorded with a named confirmer, not
  accepted from an offhand remark.
- `test-strategy-discovery-out-of-scope-needs-decider` — "nothing is out of
  scope silently": a test type is out only with a reason and a named decider.
- `document-ingestion-refuses-retype-shortcut` — "conversion is not
  migration" / "convert with a tool, not by retyping."

PILOT-53 (REQ-V2E-02) tightened six cases whose with-plugin and without-plugin
scores were both 1.0, so each grader now checks a rule plain Claude does not
follow unprompted:
- `stack-discovery-fires-on-stack-question` — the fixture now declares an
  unused `mongoose`. PASS needs "declared vs in use" (Rule 3), literal
  `[confirmed]`/`[inferred]`/`[ASK]` markers, and `.evidence/context/stack.md`.
- `stack-discovery-flags-ambiguous-stack-as-ask` — the literal `[ASK]` marker,
  and no endpoint recipe until the human resolves the conflict.
- `design-system-discovery-fires-on-component-question` — extend-before-add, a
  written justification naming the alternatives, and
  `.evidence/context/design-system.md`.
- `compliance-discovery-fires-on-regulation-question` — asks each framework's
  *role* (legal / contractual / certification / alignment) and a named owner,
  and records to `.evidence/context/compliance.md`.
- `toolchain-discovery-fires-on-connectivity-question` — the fixed class
  vocabulary (`MCP-official` … `Manual`), the fallback when a tool is
  unreachable, and `.evidence/context/toolchain.md`.
- `toolchain-discovery-flags-community-mcp-risk` — managed MCP allowlisting,
  `MCP-internal`/`REST-scripted` for writes, and the decision and its decider
  recorded in the profile.

`compliance-discovery-fires-on-regulation-question` and
`document-ingestion-fires-on-legacy-sop-migration` were also missing their
`tags:` line, so `--tag trigger` skipped them. They are now tagged.

## Running it

Most cases are read-only:

```bash
cd plugins/evidence-discovery
claude plugin eval . --tag trigger --tag non-trigger --tag behavior
```

Six cases seed a fixture repo via `context.scaffold_script` and need
`--scaffold`:

```bash
claude plugin eval . --tag scaffold --scaffold
```

To run everything in one pass:

```bash
claude plugin eval . --scaffold
```

No case in this suite grants `Write` — every skill here is graded on what it
*says* it would write (citing evidence, naming `[ASK]` items, proposing a
profile), not on an actual committed `.evidence/context/*.md` file. Add a
`needs-write` case per skill if you want to verify the actual file and its
headings, the way `evidence-sdlc`'s `intent-capture-writes-intent-file` does.

To iterate on one case cheaply:

```bash
claude plugin eval . --case <case-name> --runs 1 --ablation none
```

## CI

```bash
claude plugin eval . \
  --trust-plugin \
  --scaffold \
  --json results.json \
  --threshold 0.8 \
  --model claude-sonnet-5 \
  --judge-model claude-haiku-4-5 \
  --no-publish \
  --max-cost-usd 20
```

## Known limitations

- **Cross-plugin consumers aren't exercised.** These skills *produce*
  `.evidence/context/*.md` profiles that other plugins consume —
  `evidence-sdlc`'s `spec-and-design`/`codebase-grounded-planning`/
  `risk-tiering`, and `evidence-compliance`'s `regulatory-controls`/
  `evidence-package`, all read what `compliance-discovery` and
  `stack-discovery` write. `claude plugin eval` loads only the plugin under
  test, so this suite can verify these skills gather evidence and ask the
  right questions, but not that a downstream plugin correctly consumes the
  profile they'd produce.
- **No case grants `Write`**, so no case here confirms the actual
  `.evidence/context/*.md` file gets written with the right template
  headings — only that the skill's reasoning is correct. This mirrors the
  `evidence-sdlc` suite's approach for its own precondition-only cases, but
  is a real gap if a future regression breaks only the file-writing step.
- `stack-discovery`'s and `design-system-discovery`'s scaffolded cases use
  small, synthetic Node/Express fixtures. They don't exercise the other
  manifest types (`pom.xml`, `go.mod`, `Cargo.toml`, etc.) Rule 2 lists —
  add fixtures for those stacks if that matters for your usage.
