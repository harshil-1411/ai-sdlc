---
name: performance-testing
description: Design, run and interpret performance tests — load, stress, soak, spike, and capacity/scalability — against numeric targets agreed in the spec, with a workload model, a recorded baseline and pass/fail criteria fixed before the run. Use this whenever someone asks for load testing, stress testing, soak or endurance testing, spike testing, capacity planning, "can this handle N users", "how many requests per second", latency or throughput requirements, a performance regression, or a slow endpoint that needs proving fixed. Also use when a spec contains a latency, throughput or concurrency requirement. Read the tool (k6, JMeter, Gatling, Locust or whatever the repository uses) from the repository profile — never assume one.
---

# Performance testing

Read `.evidence/context/test-strategy.md` for the agreed targets, environments where
load is allowed, and the tool; `stack.md` for how that tool runs here; and
`deployment.md` for the topology of the environment under test. If the tool is not
recorded, say so and stop at the design. Do not pick one.

## No target, no test

A performance test without a numeric target is a benchmark that nobody can fail. Before
designing anything, the requirement must exist in `spec.md` as a number, for example
`REQ-SRCH-04: search returns p95 < 400 ms and p99 < 900 ms at 200 req/s, error rate
< 0.5%`.

- If the spec has no target, that is a **spec defect**. Send it back and ask for the
  number and its source (SLA, contract, product decision). Do not invent one, and do
  not "run it and see what we get" and then write the result in as the target.
- Targets are **percentiles plus an error-rate ceiling** at a stated load. An average
  hides the tail users actually feel. Never state or accept a target as an average.

## Choose the test type by the question being asked

| Type | Question it answers | Shape | Typical stage |
| --- | --- | --- | --- |
| **Load** | Does it meet target at expected normal and peak load? | Ramp to expected load, hold, measure | Nightly + pre-release |
| **Stress** | Where does it break, how does it fail, and does it recover? | Ramp beyond peak until a target is breached or errors climb; then drop load and watch recovery | Pre-release, after architecture changes |
| **Soak (endurance)** | Does it degrade over time — memory, connections, handles, disk, queue depth? | Expected load held for hours | Scheduled (weekly or pre-release) |
| **Spike** | Does it survive a sudden surge, and does autoscaling or queueing absorb it? | Near-instant jump to a multiple of normal, then back | Pre-release, before known events |
| **Capacity / scalability** | How does throughput change as instances or resources are added? What is the headroom? | Repeated load at stepped resource levels | Capacity planning, infra changes |

Pick the smallest set that answers the requirement. A change to one query needs a
focused load test on that path, not a full soak.

## Design rules

1. **Workload model first.** Write down the transaction mix (which operations, in
   what proportion), arrival rate or concurrency, think time, and the data
   distribution. Derive it from production telemetry where it is available. A test
   that hammers one endpoint with identical requests measures the cache, not the
   system.
2. **Open vs closed model, stated.** State whether load is generated as an arrival
   rate (open) or a fixed number of looping users (closed). Closed-model tools under-report
   latency when the system slows down (coordinated omission). Prefer an arrival-rate
   executor, or correct for it, and say which one you used.
3. **Environment parity, stated as a gap.** Record how the test environment differs
   from production: instance sizes, replica counts, data volume, caches, network
   path, third-party stubs. Results transfer only across the gaps you have named. Never
   run load against production unless `test-strategy.md` records written approval
   for it.
4. **Realistic data volume.** Test against production-scale data volumes
   (synthetic, per `test-automation`'s test-data rules). An empty database makes
   every query fast.
5. **Warm-up excluded.** Exclude the ramp and warm-up period from the measured window,
   and say how long it was.
6. **Pass/fail fixed before the run.** Write the thresholds into the test script or
   run config (the tool's own threshold mechanism) before running. Moving a threshold
   after seeing the result is the performance equivalent of loosening an assertion.
7. **Stubs for third parties.** Stub external partners at their documented rate limits and
   latencies (see `contract-testing` in evidence-integrations). Never load-test a
   partner's sandbox without their agreement.
8. **Observe the system, not just the client.** Capture server-side CPU, memory, GC,
   connection pools, queue depth and database metrics for the same window. A client
   latency number with no server evidence cannot be diagnosed.

## Baselines and regressions

- Record a **baseline** per scenario: the commit SHA, the environment, the workload
  model version, and the percentile results. Store it where the evidence profile
  says evidence lives.
- A regression is a percentile or error-rate change beyond an agreed band, compared
  against the baseline under the **same** workload model and environment. If
  anything else changed, it is a new baseline, not a comparison.
- Run the same scenario enough times to see the noise before calling a change a
  regression. One run is an anecdote.

## Stress and recovery specifics

A stress test is not finished at the breaking point. Record:
- the load at which the first target was breached, and which one
- how the system failed: slow, errors, crashed, data loss, or cascading failure
- whether it shed load gracefully (429/503 with retry hints) or fell over
- the time to recover after load dropped, and whether recovery happened without
  a human stepping in

Unrecoverable failure or data loss under stress is a **finding for the spec**, not
just a number.

## Soak specifics

Watch trends, not snapshots: memory after GC, open connections, file handles, thread
counts, disk and log growth, queue backlog. A flat latency line with steadily growing
memory is a failing soak.

## Blocks vs informs

Follow `continuous-testing`: breaching a **target in spec.md** at pre-release blocks.
Drift within the agreed band informs the reviewer. Nightly performance runs report
trends and do not gate merges.

## Evidence

Each run produces: the scenario and workload model version, the commit SHA, the
environment identity, the threshold config, percentile and error-rate results, the
server-side metrics for the window, and pass/fail against each target. Link the run
from the plan's test row and from the traceability matrix. A screenshot of a
dashboard is not a result. Link the raw result export.

## Never

- Never invent a target, or back-fill one from a result.
- Never report averages as the result.
- Never change a threshold after seeing the run.
- Never load-test production or a partner's environment without recorded written
  approval.
- Never present a single run on a non-production-like environment as proof a target
  is met in production. State the environment gap.
