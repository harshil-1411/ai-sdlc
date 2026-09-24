---
name: test-strategy-discovery
description: Establish the team's agreed test strategy — test types in scope, non-functional targets, environments, browser/device matrix, who runs manual testing and UAT, entry and exit criteria — from the repository first, then the humans, and write .evidence/context/test-strategy.md. Use at onboarding, when that file is missing or stale, and on "what's our test strategy", "set up our QA approach", "which browsers do we support", "who does UAT".
---

# Test strategy discovery

A test plan per change answers "how is this change proven". It cannot answer "what
does this team test at all", and without that answer every plan falls back to the
framework's default layer table. Performance gets skipped because no one said it
mattered. Pen testing gets skipped because no one said it was someone else's job.
This skill turns those unstated assumptions into a recorded, owned strategy.

## Do not offer — run

If a testing workflow needs the strategy and `.evidence/context/test-strategy.md` is
absent, run this skill. Do not ask "would you like me to set up a test strategy?"

## Step 1 — read before asking

Read `.evidence/context/stack.md`, `deployment.md`, `toolchain.md` and
`compliance.md` first. Then gather evidence from the repository:

- Test directories and their runners, per layer, from `stack.md` and the test config
  files themselves
- CI configuration: which jobs exist, which run per commit, per PR, nightly, pre-release
- Reporter and result-upload config (JUnit XML, Allure, test-management uploaders)
- Browser automation config: projects, browsers, devices, viewport lists, base URLs
- Performance scripts and their tools (look for load-test directories and scenario files)
- Security and static-analysis config: linter and type-checker configs, SAST rules,
  dependency-scan config, secret-scan config, suppression and baseline files
- Accessibility tooling in dependencies or test code
- Coverage config and any threshold settings
- Quarantine or skip markers on tests, and how many there are
- Environment names in deployment config

Mark every answer the repository proves as `[confirmed]` with the file that proves
it, and every answer you inferred as `[inferred]` with the reasoning. Tools that
people stopped using still leave traces, so a config file alone is `[inferred]`
until CI or a recent commit shows it running.

## Step 2 — interview for what is left

Ask **only** what Step 1 could not establish. Ask it as **one numbered batch**,
most consequential first, so the team answers once instead of across ten turns.
The order that usually matters most:

1. Test types in scope that have no evidence either way. Name each type from the
   template's list and ask in, out or deferred. Never leave one out without asking.
2. Non-functional targets as numbers: latency percentiles, throughput, concurrent
   users, error-rate ceiling, accessibility conformance level.
3. Environments: which is production-like, and where are active security scanning and
   load testing allowed?
4. The browser and device matrix, and which part runs on every PR vs nightly.
5. Who executes manual and exploratory testing, who owns UAT, and who signs the
   test summary report go/no-go.
6. Security policy: fix time by severity, pen-test cadence and provider, who may
   approve a suppression.
7. Entry and exit criteria for a release test cycle.
8. Flake quarantine window, and where the coverage tool and static-analysis baseline
   live.

Accept "don't know yet" as an answer. Record it as `[ASK]` with the question
written out. Never fill it with a default.

## Step 3 — nothing is out of scope silently

A test type is `out` or `deferred` only with a reason **and** a named decider,
for example "Performance — out; internal tool, 20 users; decided by <name>,
engineering lead". Without both, the row is `[ASK]`.

This applies with extra force to anything `compliance.md` or `risk-tiering` makes
material. If a regulated record, a signature, or an externally exposed endpoint is
in play and security or accessibility testing is recorded as `out`, say plainly that
this is a risk acceptance, and name who accepted it.

## Step 4 — write the profile

Write `.evidence/context/test-strategy.md` from the plugin's
`templates/test-strategy.md`. Every row gets a marker. Record who confirmed the
profile and the date.

Finish by presenting the remaining `[ASK]` items to the human as numbered
questions. An `[ASK]` in an area a change depends on (for example, no latency target
while a change has a performance requirement) blocks that change's test plan. It does
not block unrelated work.

## Step 5 — keep it current

Re-run when a new environment, market, browser commitment or compliance framework
appears, or when a test type moves from `deferred` to `in`. `test-strategy` and
`continuous-testing` will flag drift they notice. Either fix the profile or record
why the drift is intended.

## Never

- Never invent a numeric target. A latency number that no one agreed to becomes a
  test that passes against a made-up bar.
- Never record a test type as out of scope without a named decider.
- Never copy a strategy from another repository or from a README without
  confirming it against this repository's evidence and a human.
- Never install or configure a test tool from this skill. It records the strategy;
  changing tooling is a planned change with its own `plan.md`.
