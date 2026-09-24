# evidence-integrations eval suite

9 cases covering both skills in this plugin.

- `contract-testing` (4 cases): fires on a new integration and prioritizes
  consumer contract tests over end-to-end sandbox tests (`trigger`), stays
  silent on a purely internal unit test (`non-trigger`), pushes back when a
  team treats a large real-sandbox call suite as its whole test strategy —
  shrinking it to a credential/endpoint canary, requiring stubs generated
  from a recorded contract rather than hand-written, and naming failure-path
  or idempotency tests (`behavior`) — and refuses to hand-edit a contract
  file to make a failing test pass: it diagnoses our-code vs. their-contract
  vs. misunderstanding, re-records rather than hand-edits, and versions the
  contract instead of overwriting it (`behavior`).
- `integration-change` (5 cases): fires on a new external call and, beyond
  the trust/availability/compliance framing, requires an audit entry for the
  crossing (what, when, to whom, under whose authority), field enumeration
  with provider-side retention or residency, and a spec section / runbook
  entry (`trigger`); stays silent on a purely internal refactor
  (`non-trigger`); refuses to treat a deprecation as a quick cleanup PR
  (`behavior`); flags webhook signature, replay and idempotency on a payment
  webhook plus at least two operability points — detection/alerting,
  replay/reconciliation, contract ownership/versioning, attribution of the
  processor as actor (`behavior`); and flags the regulated-record audit-trail
  requirement when a signed record crosses to a third party (`behavior`).

PILOT-53 rewrote the graders of four cases whose with-plugin and without-plugin
scores were equal (`contract-testing-refuses-to-patch-contract-to-pass`,
`contract-testing-rejects-sandbox-suite-as-only-proof`,
`integration-change-fires-on-new-external-call`,
`integration-change-flags-webhook-idempotency-and-signature`) so they score a
rule from the skill that a baseline answer does not usually state.

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
