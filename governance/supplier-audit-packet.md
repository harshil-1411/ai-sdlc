# Supplier audit response: AI in the SDLC

Audience: customer supplier-quality teams, procurement security reviews, and RFP
questionnaires. Owner: QA/RA. Keep to two pages. Review quarterly.

> Most vendors will have no answer to "do you use generative AI in development?"
> within the next year. Having one, with evidence, is a commercial asset. Route
> this through QA/RA and Legal before it leaves the building.

## The standard questions, and where the answer comes from

**Q. Do you use generative AI in your software development lifecycle?**
Yes, as a development tool under documented controls. It does not form part of the
delivered product and does not process customer records. See the tool risk assessment.

**Q. What is the qualification status of the tool?**
Categorised as supporting development software; assurance derives from verification of
output rather than qualification of the generator, consistent with our treatment of
compilers and build tooling. Risk assessment attached, approved by QA/RA, reviewed
annually.

**Q. How do you ensure AI-authored code meets your quality standards?**
Every change carries a committed artifact chain — requirement, specification, plan,
diff, tests, review findings, approval — in version control with author and timestamp.

What the Evidence Chain gate engine enforces inside an agent session (a PreToolUse hook
that fails closed on missing `python3`, malformed input or an engine error), with the
regression cases in `plugins/evidence-sdlc/scripts/tests/engine-tests.py` that prove
each rule:

- An agent's source write — through Edit/Write/MultiEdit/NotebookEdit **or** a Bash
  command — is denied unless the change has a state record, the tier's artifacts, a
  non-stub plan, and a human approval bound to the plan's current sha256; any plan edit
  voids the approval, and edits outside the plan's claimed files are denied (cases
  V2G-01*, V2G-02*, V2G-03*, V2G-04*, V2G-12*, V2A-01*).
- The agent cannot record the approval itself: `approval.json` and `state.json` are
  control-plane files no agent tool may write, and `evidence approve` run by an agent is
  denied except in the GitHub-review mode, which checks for an approving review by an
  allowed login (cases V2A-01*, V2G-09*).
- Pushes to protected branches and agent merges (`gh pr merge`, `gh api` merge or
  protection calls) are denied (cases V2G-05*); commits need the tracker key in the
  message, an `Agent-Session` trailer, and a clean secret scan of the staged diff
  (cases V2G-07*, V2A-03*, V2K-01*); pushes and PRs need the tier's review agents to
  have been run (cases V2S-04*).

Limits we state rather than hide: the local approval identity is the machine's
`git user.email` (whoever is at the keyboard), not a cryptographic identity — GitHub
approval mode is identity-bound; these gates act on the agent, not on a human working
outside it; and **server-side branch protection with CODEOWNERS on the hosting
platform remains the authoritative merge control**, configured by us, not by the
plugin. Automated test and lint gates run in repository CI once the provided workflow
(`.github/workflows/ci.yml`) is enabled on the host.

**Q. How is traceability maintained?**
Requirement IDs originate in the specification and flow to test cases and to the
traceability matrix. Sample export available on request.

**Q. What happens if AI-authored code causes a defect in our validated instance?**
Handled under our deviation and CAPA procedure, with customer notification thresholds
defined. See the deviation runbook.

**Q. Could our data or documents be exposed to the AI vendor?**
No. Development environments hold no customer production data. Tool access to
credentials, secrets and network egress is restricted by centrally managed settings
(permission deny rules and sandbox network allowlist) that engineers cannot override
locally, and the gate engine denies secrets detected in written content, command text
or staged diffs without echoing the value (engine cases V2K-01*). Secret detection is
pattern-based and will not catch every credential format.

**Q. What controls exist around changes to the AI configuration?**
The instructions and policies steering the agent are version-controlled and reviewed
like code. The gate configuration is protected in-session: agents cannot write
settings, the policy file, hooks, approval records or the audit log (engine cases
V2G-09*), and a repository's own policy can only tighten the organisation policy
(cases V2X-01*). The gate engine's behaviour is regression-tested by
`engine-tests.py` (every case prefixed with its requirement ID), and repository CI
runs that suite, the CLI tests and a plugin version-bump check on every change once
the provided workflow is enabled on the host. The skill/agent evaluation suite
(`plugins/*/evals/`) is run on configuration changes by manual dispatch, because it
calls the model; it is not an automatic per-commit gate. See
`governance/model-and-config-change-control.md`.

**Q. Can you show which agent made a given change?**
Yes. Every agent tool call and every gate denial (with rule and reason) is written to a
hash-chained log at `.evidence/audit/<session>.jsonl`, committed with the change;
`evidence audit verify` detects an altered or removed line (engine cases V2A-02*). Each
agent commit carries an `Agent-Session:` trailer linking it to that log. The log is
tamper-evident, not tamper-proof: someone with shell access outside the agent could
rewrite the whole chain, which is why we also export telemetry off-box (see
`governance/records-retention.md`).

## Evidence pack to hand over

1. This document.
2. The approved tool risk assessment (signatures page).
3. A redacted sample artifact chain for one representative change.
4. A sample traceability export.
5. The controls summary table from the risk assessment, and the relevant rows of
   `governance/control-mapping.md` (not an attestation).
6. Output of `evidence audit verify` and `evidence metrics --json` for the sample change.

Do not hand over: session transcripts, source code, or the managed settings file.
