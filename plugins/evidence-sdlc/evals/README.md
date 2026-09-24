# evidence-sdlc eval suite

29 cases covering all 9 skills in this plugin: for each skill, at least one
case that should trigger it (`trigger`), one that should not (`non-trigger`),
and one that checks the skill actually follows its own non-obvious rule
(`behavior`) — e.g. schema-migration refusing to combine an add and a drop,
secure-api-review rating a missing ownership check Critical, spec-and-design
stopping when `.evidence/context/stack.md` is missing.

## Running it

Most cases are read-only and need no extra grants:

```bash
cd plugins/evidence-sdlc
claude plugin eval . --tag trigger --tag non-trigger --tag behavior
```

Three cases seed a fixture repo (fake `.evidence/context/`, `intent.md`,
`spec.md`) via `context.scaffold_script` before Claude starts, so they need
`--scaffold`:

```bash
claude plugin eval . --tag scaffold --scaffold
```

One case (`intent-capture-writes-intent-file`) actually commits a file to
disk and needs `Write` granted:

```bash
claude plugin eval . --tag needs-write --allow-tools Write
```

To run everything in one pass:

```bash
claude plugin eval . --scaffold --allow-tools Write
```

To iterate on a single case cheaply while tightening a skill's `description`:

```bash
claude plugin eval . --case <case-name> --runs 1 --ablation none
```

## CI

```bash
claude plugin eval . \
  --trust-plugin \
  --scaffold \
  --allow-tools Write \
  --json results.json \
  --threshold 0.8 \
  --model claude-sonnet-5 \
  --judge-model claude-haiku-4-5 \
  --no-publish \
  --max-cost-usd 20
```

## Known limitation: cross-plugin skill references

Several skills here call out to skills that live in *other* plugins in this
marketplace — `test-strategy` / `traceability-ids` (`evidence-quality`),
`regulatory-controls` / `evidence-package` (`evidence-compliance`),
`integration-change` (`evidence-integrations`), and the optional
`decision-council` (`examples/skills/`). `claude plugin eval` loads only the
plugin under test, so a run of this suite cannot verify that those
cross-plugin handoffs actually happen — only that this plugin's own skills
state the right intent (e.g. "apply the `regulatory-controls` skill"). The
three bundled agents (`codebase-cartographer`, `security-reviewer`,
`verifier`) are self-contained in this plugin and are fully covered.

Every case here is a starting point, not a ceiling — add more as you find
gaps, and re-run `--case <name> --runs 1` while tightening a skill's
`description` whenever a `trigger` case's `Δ` comes back near zero.
