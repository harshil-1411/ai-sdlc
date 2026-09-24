# Repository profile — test strategy

What this team has agreed to test, at which stage, with which tool, owned by whom.
Written by `test-strategy-discovery`; read by `test-strategy`, `continuous-testing`
and every test-type skill in `evidence-quality`. Every line is marked `[confirmed]`,
`[inferred]` or `[ASK]`.

Confirmed by: <name, role>   Date: <yyyy-mm-dd>

## Test types in scope

`Scope` is `in`, `out` or `deferred`. `out` and `deferred` need a reason and a named
decider, or the row is `[ASK]`.

| Test type | Scope | Reason (if out/deferred) | Decided by | Stage it runs at | Tool | Owner | Marker |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Unit | | | | | | | |
| Integration / API | | | | | | | |
| Contract | | | | | | | |
| End-to-end UI | | | | | | | |
| Cross-browser / device | | | | | | | |
| Visual regression | | | | | | | |
| Accessibility | | | | | | | |
| Localisation | | | | | | | |
| Performance — load | | | | | | | |
| Performance — stress | | | | | | | |
| Performance — soak | | | | | | | |
| Performance — spike | | | | | | | |
| Static analysis — lint / format / types | | | | | | | |
| Static analysis — SAST | | | | | | | |
| Dependency / SCA scanning | | | | | | | |
| Secret scanning | | | | | | | |
| Container / IaC scanning | | | | | | | |
| DAST | | | | | | | |
| Fuzzing | | | | | | | |
| Penetration testing | | | | | | | |
| Manual / exploratory | | | | | | | |
| UAT | | | | | | | |
| Legacy characterization | | | | | | | |

## Non-functional targets

Numbers only. A target with no number is `[ASK]`, not a blank.

| Target | Value | Measured where | Source (SLA, contract, product decision) | Marker |
| --- | --- | --- | --- | --- |
| Latency (p95 / p99) per critical endpoint or journey | | | | |
| Throughput (requests or transactions per second) | | | | |
| Concurrent users (normal / peak) | | | | |
| Error rate ceiling under load | | | | |
| Soak duration and resource-growth limit | | | | |
| Accessibility conformance target (e.g. WCAG 2.2 AA) | | | | |

## Environments

| Environment | Purpose | Production-like? (data volume, topology, config) | Active security scanning allowed? | Performance testing allowed? | Marker |
| --- | --- | --- | --- | --- | --- |

## Browser and device matrix

| Browser / device | Version policy | Tier (every PR / nightly / pre-release) | Marker |
| --- | --- | --- | --- |

## Automation and manual ownership

| Question | Answer | Marker |
| --- | --- | --- |
| Target automation share for regression | | |
| Who executes manual and exploratory testing | | |
| Who owns UAT and signs it off | | |
| Who signs the test summary report go/no-go | | |

## Security testing cadence and policy

| Item | Answer | Marker |
| --- | --- | --- |
| Fix-time policy by severity (critical / high / medium / low) | | |
| Penetration test cadence, provider, scope | | |
| Who may approve a suppression | | |
| Written authorisation for any production scanning (link) | | |

## Entry and exit criteria

| Criterion | Entry (testing may start when…) | Exit (release may proceed when…) | Marker |
| --- | --- | --- | --- |

## Quality policies

| Policy | Value | Marker |
| --- | --- | --- |
| Flake quarantine window (days) | | |
| Coverage tool and how it is run | | |
| Static-analysis baseline location | | |
| Visual-regression baseline approver | | |

## Open questions — [ASK]
