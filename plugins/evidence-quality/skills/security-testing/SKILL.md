---
name: security-testing
description: Plan, run and triage security testing of the running system and supply chain — dependency/SCA, secret, container and IaC scanning, DAST, fuzzing, penetration testing — under one findings policy (severity, fix time, suppression with owner and expiry). Use on vulnerability scans, CVE or dependency alerts, OWASP ZAP/Burp, fuzzing, pen-test prep or retest, or a request to suppress or accept a security finding. Read tools and policy from the profile.
---

# Security testing

Read `.evidence/context/test-strategy.md` for which security test types are in scope,
the fix-time policy, who may approve a suppression, and which environments allow
active scanning. Read `toolchain.md` and `stack.md` for the tools. If a type in scope
has no recorded tool, say so and stop at the design.

`secure-api-review` (evidence-sdlc) reviews the design and the diff. It explicitly
says it is not a substitute for SAST, DAST, dependency scanning or pen testing. This
skill is that testing. Static-analysis tool configuration, baselines and rule changes
belong to `static-analysis`. **What to do about a security finding**, from whatever
source, is this skill's policy.

## What each test type finds, and where it runs

| Type | Finds | Runs | Blocks? |
| --- | --- | --- | --- |
| **SCA / dependency scanning** | Known CVEs in direct and transitive dependencies, licence violations | Every commit; nightly re-scan of the default branch, because new CVEs appear against unchanged code | New critical/high: yes |
| **Secret scanning** | Keys, tokens, passwords in code and history | Pre-commit + every commit; full-history scan at onboarding | Any live secret: yes |
| **Container image scanning** | OS-package and runtime CVEs, running as root, bloated attack surface | On image build; nightly on deployed images | New critical/high: yes |
| **IaC scanning** | Public buckets, open security groups, missing encryption, over-broad IAM | Every commit touching infra | Critical/high: yes |
| **DAST** | Runtime issues: injection, auth/session flaws, headers, CORS, exposed endpoints | Deploy-to-test stage (baseline scan per deploy, full scan nightly) | Confirmed high: yes |
| **Fuzzing** | Crashes, hangs, and unhandled input in parsers, decoders and API handlers | Scheduled; long runs nightly/weekly on parsers and file handlers | New crash: yes |
| **Penetration testing** | Chained, logic and authorisation flaws that tools miss | Per cadence in the profile, and before major releases or new external surfaces | Findings enter the same policy |

## Rules for active testing (DAST, fuzzing, pen testing)

- **Targets come from the profile, never from the conversation.** Only scan hosts and
  environments `test-strategy.md` names as allowing active scanning. If a request names
  a target not in the profile, stop and ask.
- **Never production** without a written authorisation linked in the profile, with
  scope, window and a named approver.
- **Authenticated scans.** An unauthenticated DAST scan tests the login page. Scan as
  each role that matters, including a second tenant, so object-level authorisation and
  tenant isolation are exercised. Use dedicated test accounts, never real users.
- **Seed the scanner.** Give DAST the OpenAPI spec or a recorded journey, so it reaches
  the endpoints that matter instead of only what it can crawl.
- **Fuzz the parsers first.** File uploads, import formats, decoders, and anything
  that takes structured input from outside. Keep the corpus and every crashing input
  as a regression case.
- **Pen test scope is written down**: in and out of scope, test accounts, rules of
  engagement, contacts. Every fixed finding gets a **retest** by the tester, and the
  retest result is the evidence, not the fix commit.

## Findings policy — one policy for every source

1. **Severity** comes from the tool's rating adjusted for this system's context
   (exploitability, exposure, data involved). Record the reason for any adjustment.
   Downgrading a finding is a decision with a name on it.
2. **Fix time by severity** is read from `test-strategy.md`. If none is recorded, that
   is an `[ASK]` for the security owner. Do not invent one.
3. **Baseline vs new.** When a scanner is first introduced, record the existing
   findings as a baseline with an owner and a remediation plan, and block on **new**
   findings only. The baseline may only shrink.
4. **Suppression requires all of:** a specific reason (false positive with the
   proof, or accepted risk with the compensating control), a named owner, an
   approver from the profile's list, and an **expiry date**. It must sit in the tool's
   suppression file, next to the finding. A suppression missing any of these is
   rejected. A suppression with no expiry is a permanent silent acceptance.
5. **Expired suppressions reopen** the finding. They are never renewed silently.
6. **Every fixed vulnerability gets a regression test** at the lowest layer that can
   prove it (per `test-strategy`).

## Blocks vs informs

As in `continuous-testing`: new critical/high findings, live secrets, and confirmed
DAST highs block. Medium and low findings inform the reviewer and follow the fix-time
policy. **Never gate a merge on a total finding count.** Gate on new findings above a
severity.

## Evidence

Per run: tool and version, rule-set or database version, target and environment,
commit SHA, the raw report export, and the list of new, fixed and suppressed findings
with their suppression records. For pen tests: the scope document, the report, and
the retest results. Link each from the tracker key.

## Never

- Never scan a target that is not in the profile, and never scan production without
  written authorisation.
- Never suppress a finding without a reason, an owner, an approver and an expiry.
- Never close a finding because the scanner stopped reporting it. Confirm the fix.
- Never treat a clean scan as proof of security. Record what it covered.
- Never commit a real secret into a test fixture to "test the scanner".
