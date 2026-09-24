# evidence-integrations eval suite

9 cases covering both skills in this plugin.

- `contract-testing` (4 cases): fires on a new integration and prioritizes
  consumer contract tests over end-to-end sandbox tests (`trigger`), stays
  silent on a purely internal unit test (`non-trigger`), pushes back when a
  team treats a large real-sandbox call suite as its whole test strategy
  (`behavior`), and refuses to silently patch a contract file to make a
  failing test pass without first establishing why it changed (`behavior`).
- `integration-change` (5 cases): fires on a new external call and covers the
  trust/availability/compliance framing rather than just security
  (`trigger`), stays silent on a purely internal refactor (`non-trigger`),
  refuses to treat a deprecation as a quick cleanup PR (`behavior`), flags
  webhook signature verification and idempotency on a payment webhook design
  (`behavior`), and flags the regulated-record audit-trail requirement when a
  signed record crosses to a third party (`behavior`).

All 9 are read-only — no `Write` grant, no scaffold needed, since neither
skill has a stated precondition file to seed.

## Running it

```bash
cd plugins/evidence-integrations
claude plugin eval . --trust-plugin
```

To iterate on one case cheaply:

```bash
claude plugin eval . --case <case-name> --runs 1 --ablation none
```

## CI

```bash
claude plugin eval . \
  --trust-plugin \
  --json results.json \
  --threshold 0.8 \
  --model claude-sonnet-5 \
  --judge-model claude-haiku-4-5 \
  --no-publish \
  --max-cost-usd 15
```

## Known limitations

`integration-change`'s own description says it "runs ALONGSIDE
`secure-api-review` rather than being replaced by it" and its body says to
"apply the `agent-trust-boundaries` skill" for inbound payloads reaching a
model — both of those skills live in `evidence-sdlc`, a different plugin.
`claude plugin eval` loads only the plugin under test, so this suite cannot
verify that handoff actually happens in a real session where both plugins are
installed together — only that `integration-change` states the right intent
(trust boundary framing, idempotency, audit trail) on its own. The
`covers-three-boundaries` and `flags-webhook-idempotency-and-signature`
graders check the parts `integration-change` owns directly; they do not check
whether `secure-api-review` or `agent-trust-boundaries` would also fire
correctly alongside it.
