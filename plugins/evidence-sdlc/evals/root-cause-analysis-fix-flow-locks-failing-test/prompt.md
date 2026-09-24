---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
tags: [behavior, root-cause-analysis]
---

BUG-311: since last Tuesday's release, some EUR invoices total one cent less
than the sum of their lines. Repro: three lines of €10.005 each → expected
invoice total €30.02 (per-line rounding, which is what the contract says),
actual €30.01. Code path: `InvoiceService.total()` in
`src/billing/invoice.ts`; there's no error or stack trace, the number is just
wrong. Tuesday's release had ~40 commits, a few of them in `src/billing/`.
It's a Tier 2 change per our usual rules. Walk me through exactly how you'll
take this from here to a merged fix — the concrete steps and commands, in
order.
