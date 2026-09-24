# evidence-quality eval suite

30 cases covering all 10 skills in this plugin: `continuous-testing`,
`test-automation`, `test-strategy`, `testrail-authoring`, `traceability-ids`,
`e2e-ui-testing`, `accessibility-testing`, `performance-testing`,
`security-testing`, `static-analysis`.
For each skill: a `trigger` case, a `non-trigger` case, and a `behavior` case
that checks the skill's actual non-obvious rule rather than just whether it
fired — e.g. `test-automation` refusing to hide flake behind a retry,
`testrail-authoring` refusing to assume TestRail write access it hasn't
confirmed, `traceability-ids`' parent/child key format for cross-repo changes. PILOT-51
added behavior cases for the new type skills: `performance-testing` refusing to
invent a target, `security-testing` requiring owner and expiry on a suppression,
`static-analysis` refusing a blanket disable, `e2e-ui-testing` not choosing a
tool on the team's behalf, and `accessibility-testing` refusing a conformance
claim from an automated scan alone.

## Running it

Read-only cases need no extra grants:

```bash
cd plugins/evidence-quality
claude plugin eval . --tag trigger --tag non-trigger --tag behavior
```

One case seeds a fixture toolchain profile (TestRail fields + a recorded
write decision) via `context.scaffold_script`, so it needs `--scaffold`:

```bash
claude plugin eval . --tag scaffold --scaffold
```

To run everything in one pass:

```bash
claude plugin eval . --scaffold
```

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

## Known limitations: cross-plugin references

`test-strategy` and `testrail-authoring` both reference skills that live in
*other* plugins in this marketplace: `risk-tiering` (`evidence-sdlc`, for
what counts as a regulated/Tier 3 path) and `regulatory-controls` /
`evidence-package` (`evidence-compliance`, for the signature-manifestation
control and the evidence profile). `claude plugin eval` loads only the
plugin under test, so this suite cannot verify those handoffs — only that
this plugin's own skills state the right intent. The two bundled agents,
`test-designer` and `flake-triage`, are self-contained in this plugin and
are exercised (as an indicator, not a scored requirement) by the
`test-strategy-fires-on-spec-review` and `test-automation-fires-on-flaky-test`
cases respectively.

Add more cases as gaps turn up, and re-run `--case <name> --runs 1` while
tightening a skill's `description` whenever a `trigger` case's `Δ` comes back
near zero.
