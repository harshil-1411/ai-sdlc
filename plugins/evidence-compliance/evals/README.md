# evidence-compliance eval suite

8 cases across the plugin's 2 skills:

- `regulatory-controls`: fires-on-regulated-change, reports-na-not-silence (every
  control gets an explicit verdict, N/A included), stops-without-compliance-profile
  (precondition), no-fire-on-unrelated.
- `evidence-package`: fires-on-release-prep (derives from the artifact chain rather
  than writing a generic report, flags `NO COVERAGE`), flags-no-coverage (treats a
  requirement with no automated test as a blocking finding), sets-evidence-profile-if-missing
  (Step 0's "read or set the evidence profile" rule), no-fire-on-unrelated.

## Running it

Most cases seed a fixture `.evidence/context/compliance.md` (and, for
`evidence-package`, a fake `intent.md`/`spec.md`/`plan.md` artifact chain for
tracker FIX-101) via `context.scaffold_script`, so nearly everything here needs
`--scaffold`:

```bash
cd plugins/evidence-compliance
claude plugin eval . --scaffold
```

The one case with no scaffold need is `regulatory-controls-stops-without-compliance-profile`
(it deliberately runs in the empty default workspace to prove the precondition
holds) and the two `non-trigger` cases.

To iterate on one case cheaply:

```bash
claude plugin eval . --case <case-name> --runs 1 --ablation none --scaffold
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

- `regulatory-controls` and `evidence-package` are both read by, and read from,
  skills in *other* plugins in this marketplace: `risk-tiering` and `spec-and-design`
  (`evidence-sdlc`) reference `regulatory-controls`/`evidence-package` directly, and
  `evidence-package` reads the same `.evidence/context/compliance.md` that
  `evidence-discovery`'s `compliance-discovery` skill writes. `claude plugin eval`
  loads only the plugin under test, so this suite cannot verify that a real
  `compliance-discovery` run produces a profile these two skills can actually
  consume, or that `spec-and-design`'s "apply the regulatory-controls skill" handoff
  really invokes this plugin's skill end to end — only that each skill behaves
  correctly given a profile shaped like the real thing.
- The `compliance-reviewer` agent (bundled in this plugin, `agents/compliance-reviewer.md`)
  isn't covered by any case here yet — it's invoked as a sub-agent dispatch, similar to
  how `evidence-sdlc`'s eval suite grades `codebase-cartographer` dispatch, and would
  need its own case with a diff-shaped fixture to review.
