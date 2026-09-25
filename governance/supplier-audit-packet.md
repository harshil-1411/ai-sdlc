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
- The agent cannot record a *valid* approval itself, **when the organisation deploys a
  signing key and the sandbox** (the managed-settings template does both). Approvals and
  audit entries are HMAC-signed with `EVIDENCE_SIGNING_KEY`, which the hooks can read and
  the agent cannot. The sandboxed shell has the variable hidden and the file denied. The
  Read tool is denied by permission rules with `//` absolute paths and by the engine's own
  Read hook. (The 2.0.0 template wrote those rules with one `/`, which Claude Code resolves
  relative to the project, so they did not deny the Read tool. A key was exposed that way
  on 2026-09-24; fixed in the 2.0.2 template, with a canary step in
  docs/managed-settings.md.) An unsigned or forged `approval.json` is rejected
  (cases V2A-01* "re-audit"). Every agent tool that writes files is also denied on
  `approval.json`/`state.json`, and `evidence approve` run by an agent is denied except
  to record a GitHub review by an allowed login who is not the PR author. **Without a
  signing key** (UNSIGNED mode, announced at session start), a determined agent running
  code the gates cannot inspect could forge the file; the integrity monitor would record
  the write but not prove who made it.
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

Since 2.1.0, **change control rests on the `verify-range` check**, not on the local gates. It is
a `pull_request_target` job that runs the base branch's copy of the workflow, so a pull request
can't alter the check that judges it. It reads every commit with git plumbing and fails the PR
unless:
- each commit carries the change key and an agent-session or human-commit trailer;
- every changed path is within the approved plan;
- no secret or oversize file is added;
- audit logs only grow, and change records are not rolled back;
- a code owner approved the PR's head commit on GitHub.

We make it a required status check. **Residual risk (ADR-0003 §4), stated rather than hidden:**
the signing key is present in the local hook process, which runs git in a repository the agent
can shape, so a determined agent could expose it and forge local records. The merge decision
does not depend on that key: it requires the GitHub code-owner review. Key isolation is
scheduled (PILOT-61). Admin direct pushes are reported after the fact, not prevented.

Since 2.2.0 (ADR-0005) the local integrity monitor is detection with **verified** automatic undo:
a control-plane change it restores and re-reads, or removes, is recorded closed rather than
waiting for a human, up to a per-session cap, and the record is kept and shown to the code owner
by `verify-range`. **Unresolved violations still block** push and source edits until a human
clears them. Configuration edits by the human (root-owned managed settings, permission grants and
tightening in `settings.local.json`, Claude Code's own `~/.claude.json` bookkeeping) are logged,
not charged to the agent; edits that could run commands are always undone.

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
hash-chained, and when a signing key is deployed, signed, log at
`.evidence/audit/<session>.jsonl`. The commit gate refuses a commit that leaves the
change's audit log, state and approval unstaged, so they are committed with the change
(case REQ-V2A-02 "commit without the change's evidence"). `evidence audit verify` detects
an altered or removed line and, with a key, an unsigned one (engine cases V2A-02*). Each
commit made in a gated agent session carries an `Agent-Session:` trailer linking it to
that log, and each entry records the model the session ran. The log is
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
