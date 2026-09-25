# Control mapping: SOC 2, ISO/IEC 27001:2022, NIST SSDF

Owner: [ASK — proposed: Information Security with QA/RA]. Review cycle: on every
change to the gate engine or default policy, and annually.

> **This is not an attestation, a certification claim, or audit evidence on its own.**
> It maps controls in three public frameworks to what Evidence Chain does, so an
> auditor or security reviewer can see which parts of a control the tooling helps with
> and which it does not. Whether your organisation meets any control is decided by
> your own control owners and your auditor. See `DISCLAIMER.md`.

The detailed control sets that skills apply during work are in
`plugins/evidence-compliance/skills/regulatory-controls/references/soc2.md`,
`references/iso-27001.md` and `references/nist-ssdf.md`. This file maps controls to
**mechanisms**; those files describe what a change must do to satisfy each control.

## Conditions for ENFORCED

Rows marked ENFORCED assume the managed-settings template is deployed: plugins
force-enabled, the sandbox on, and `EVIDENCE_SIGNING_KEY` set for the Claude Code process and denied to
the sandbox. Without the key, approval and audit integrity drop from *enforced* to *detected*: the
integrity monitor records unapproved writes, but a forged record cannot be told from a real one.

### Where change control rests (2.1.0, ADR-0004)

The in-session gates are **advisory for merged history**. **Residual risk (ADR-0003 §4):** the
signing key lives in the hook process, which runs git in a repository the agent shapes. A
race with a command the agent started, or a same-user process reading the hook's environment,
can expose the key, and with it every local record could be forged. This risk is accepted and
stated until PILOT-61 isolates the key.

So change control (CC8.1, A.8.32) rests on the **`verify-range` required status check**: a
`pull_request_target` job that runs the base branch's workflow, reads the PR's commits with git
plumbing, and fails the PR unless every commit carries the change key and a session or human
trailer, every path is within the approved plan's claims, no secret or oversize blob is added,
audit logs only grow, change records are neither rolled back nor forged into another change's
history, and a **code owner approved the PR's head commit on GitHub**. The last condition doesn't
depend on the signing key. It holds only when the owner makes `verify-range` a required check and
keeps code-owner review required (OWNER ACTION). Admin direct pushes are reported after the fact
by `verify-range --push-report`, not prevented.

### The local monitor since 2.2.0 (ADR-0005)

The integrity monitor is **detection with verified automatic undo**. A control-plane change it
restores (re-read equals the snapshot) or removes (the path is gone) is recorded closed at birth
(`resolved: "restored"`), bounded by `auto_resolve_max_per_session` per session, and stays in the
signed record and the audit log. **Unresolved violations still block** push, pull requests and
source edits until a human clears them: anything not undone, undone without verification, over
the cap, or outside the control plane. `verify-range` rule 5 accepts a closed-at-birth entry only
when it is a verified restore of an auto-resolvable rule, and prints each one for the code owner;
any other entry that first appears closed without a signed clear fails the PR. Configuration edits
are judged by effect: `settings.local.json` grants and tightening, root-owned system config the
session's user could not write, and `~/.claude.json` bookkeeping are logged, not charged. Tier 3 in
`acceptEdits` or `auto` depends on reading from GitHub that `verify-range` is required and pinned to
GitHub Actions. Nothing here moves authority from `verify-range` and code-owner review.

## How to read the Status column

| Status | Meaning |
| --- | --- |
| **ENFORCED** | A deterministic gate in the Evidence Chain engine denies the non-compliant agent action. It fails closed (missing `python3`, malformed input or an engine error means deny). Each claim cites its regression cases in `plugins/evidence-sdlc/scripts/tests/engine-tests.py` (labels prefixed with the requirement ID, e.g. "V2G-05*"). It acts on the **agent inside a Claude Code session**, not on humans working outside it, and it is defence-in-depth, not a replacement for server-side controls. |
| **GUIDED** | A skill or agent applies the control while work is done. It depends on the model following instructions; it is checked by evals and review, not guaranteed. |
| **OWNER ACTION** | Outside what a plugin can do. The adopting organisation must configure or operate it (hosting platform, IdP, CI, collector, scanners, processes). |

Where more than one applies, the row says which part is which.

## Evidence queries

| Query | Shows |
| --- | --- |
| `evidence audit verify` | Every `.evidence/audit/*.jsonl` hash chain is intact (tamper-**evident**, not tamper-proof). |
| `evidence metrics --json` | `gate_denials` by rule, `self_approval_attempts`, `stage_skip_rate`, changes by stage, agent sessions logged. |
| `evidence change list --json`, `evidence change status <KEY> --json` | Each change's tier, kind, stage, missing artifacts, approval validity, missing review agents. |
| `.evidence/changes/<KEY>/approval.json` | Approver, method (prompt / terminal / GitHub), plan sha256 approved. |
| `evidence gaps` / `evidence export` | Requirement → test → result coverage; `UNPROVEN`, `SELF-ASSERTED`, `NO COVERAGE`; `approved_by`, `agent_sessions`. |
| `git log --grep 'Agent-Session:'` | Agent-authored commits and the session (audit log) behind each. |
| `grep '"event": "deny"' .evidence/audit/*.jsonl` | Individual gate denials with rule and reason. |
| `python3 plugins/evidence-sdlc/scripts/tests/engine-tests.py` | The gates behave as documented (run locally, and in CI once `.github/workflows/ci.yml` is enabled). |
| Session-start canary | Each session prints "Evidence Chain gates live"; if it does not, the gates are not running in that deployment. |

## SOC 2 (2017 Trust Services Criteria, Common Criteria)

| Control | Evidence Chain mechanism | Status | Evidence query | Gaps / owner |
| --- | --- | --- | --- | --- |
| CC6.1 Logical access security | Agent tool scope only: control-plane protection (agents cannot write settings, policy, hooks, approvals, audit log — V2G-09*); managed-settings permission denies and sandbox. | OWNER ACTION (primary); ENFORCED for agent tool scope | `engine-tests.py` V2G-09*; `managed-settings.json` | Logical access to systems is the platform's: IdP/SSO, MFA, repo host, cloud IAM. Evidence Chain provides none of it. |
| CC6.2 User registration and authorisation | Training as a prerequisite to access (`training-matrix.md`). | OWNER ACTION; GUIDED (policy text) | Training records | Provisioning/deprovisioning of engineers and of Claude seats is entirely yours (IdP, admin console). |
| CC6.3 Role-based access, least privilege, segregation of duties | Agent cannot approve its own plan (V2A-01*), cannot write approval/state records (V2G-09*), cannot merge or push to protected refs (V2G-05*); read-only review agents are write-denied (V2K-03*); T3 changes denied under auto-accept modes (V2S-03*). | ENFORCED (agent/human separation); OWNER ACTION (human roles, CODEOWNERS) | `approval.json` approver vs commit author; `evidence metrics --json` → `self_approval_attempts` | Local approver identity is `git user.email` at the keyboard, not cryptographic; use GitHub approval mode for identity binding. Human role design is yours. |
| CC6.6 Boundary protection | Sandbox network allowlist in managed settings; `agent-trust-boundaries` skill for untrusted content; `secure-api-review` for product boundaries. | OWNER ACTION (set allowlist domains); GUIDED | `managed-settings.json` | No network enforcement beyond Claude Code's sandbox; prompt-injection defence is guidance. |
| CC6.8 Prevent/detect unauthorised or malicious software | Dangerous git config (`core.hooksPath`, `alias.*`, `credential.*`, `filter.*`, `include.path`) denied (V2K-02*); control plane protected (V2G-09*); `allowManagedHooksOnly` and `strictKnownMarketplaces` in managed settings. | ENFORCED (in-session); OWNER ACTION (set marketplace value, deploy managed settings, run canary) | `engine-tests.py` V2K-02*, V2G-09*; canary | No malware or dependency (SCA) scanning is shipped. |
| CC7.1 Detect configuration changes and vulnerabilities | Agent writes to configuration are denied or logged; every agent write is in the audit log; plugin version-bump CI check. | ENFORCED (logging, control plane); OWNER ACTION (enable CI, vulnerability scanning) | `evidence audit verify`; audit log entries by path; CI results | No vulnerability scanning; configuration drift outside the repo (e.g. host settings) is not observed. |
| CC7.2 Monitor for anomalies | Gate denials with rule and reason in the audit log; `evidence metrics`; OTel env block shipped in managed settings. | ENFORCED (recording); OWNER ACTION (collector endpoint, alerting, review) | `evidence metrics --json` → `gate_denials`; `grep '"event": "deny"'` | No alerting is shipped. Someone must look at denials and self-approval attempts. |
| CC8.1 Change management | Source write requires an active change with tier artifacts, a non-stub plan and a human approval bound to the plan sha256 (V2G-04*, V2A-01*); claims scope (V2G-12*); tier floors (V2S-02*); change ticket on controlled paths (V2G-08*); review agents before push/PR (V2S-04*); key + `Agent-Session` in commits (V2G-07*, V2A-03*); test protection in fixes (V2G-10*); Bash writes held to the same rules (V2G-02*). | ENFORCED at merge by `verify-range` (ADR-0004 rules 0–5, a required `pull_request_target` check; `cli-lifecycle-tests.py` IMH-19*), and in-session (agent, advisory: ADR-0003 residual risk); OWNER ACTION (make `verify-range` required, keep code-owner review, re-run after approval) | `verify-range` check run on each PR; `evidence change list --json`; `evidence metrics --json` → `stage_skip_rate`; `approval.json`; `evidence gaps`; `git log --grep 'Agent-Session:'` | Human commits need a `Human-Commit:` trailer and the key, and are covered by the head-commit review. Admin direct pushes are reported (`--push-report`), not prevented. Fork PRs fail by design. |

## ISO/IEC 27001:2022 Annex A

| Control | Evidence Chain mechanism | Status | Evidence query | Gaps / owner |
| --- | --- | --- | --- | --- |
| A.5.8 Information security in project management | Risk tier per change with policy tier floors (V2S-02*); `spec-and-design` applies the security standard; T3 requires intent + spec + plan (V2G-04*). | ENFORCED (tier floors, artifacts exist); GUIDED (content) | `evidence change status <KEY> --json`; spec.md | Quality of the security analysis in the spec is reviewed by humans. |
| A.5.15 Access control | As CC6.1 / CC6.3. | OWNER ACTION; ENFORCED (agent scope) | as CC6.3 | Access-control policy and IdP are yours. |
| A.8.4 Access to source code | Agents cannot push to protected refs or merge (V2G-05*), cannot write control-plane files (V2G-09*). | ENFORCED (agent); OWNER ACTION (repo host permissions, branch protection) | `engine-tests.py` V2G-05*, V2G-09* | Read access and human write access are the host's. |
| A.8.8 Management of technical vulnerabilities | `security-reviewer` must have run before push/PR at T2+ (V2S-04*); it reports every Critical/High. | ENFORCED (review ran); GUIDED (findings); OWNER ACTION (scanning, patching) | audit log `agent-completed` events; `evidence change status` → missing agents | No SCA, container or infrastructure scanning is shipped. |
| A.8.9 Configuration management | Tighten-only policy layering (V2X-01*); control plane (V2G-09*); managed settings with `requiredMinimumVersion`; version-bump CI check. | ENFORCED (in-session); OWNER ACTION (deploy managed settings, pin model, enable CI) | `engine-tests.py` V2X-01*; CI | The template does not pin a model; see `model-and-config-change-control.md`. |
| A.8.15 Logging | Hash-chained `.evidence/audit/<session>.jsonl`: every agent write/Bash call, every deny with rule and reason, agent runs, approvals; committed with the change (enforced by the commit gate); signed when a key is deployed (V2A-02*). | ENFORCED | `evidence audit verify` | Tamper-evident, not tamper-proof; off-box copy (OTel collector or CI artifact) is an owner action. Retention decisions: `records-retention.md`. |
| A.8.16 Monitoring activities | OTel env block in managed settings; `evidence metrics`. | OWNER ACTION (endpoint, monitoring); ENFORCED (records exist) | `evidence metrics --json` | No alerting shipped. |
| A.8.24 Use of cryptography | Crypto/signing paths have a T3 tier floor and need a change ticket (V2S-02*, V2G-08*); secrets denied in content and diffs (V2K-01*); `secure-api-review` covers key handling. | ENFORCED (process gates); GUIDED (design); OWNER ACTION (key management) | `engine-tests.py` V2S-02*, V2G-08*, V2K-01* | Algorithm and KMS choices are reviewed by humans. |
| A.8.25 Secure development life cycle | The lifecycle itself: intent → spec → plan → approved → implementing → verified → released (V2S-01*), with the gates above. | ENFORCED (stages, approval); GUIDED (artifact content) | `evidence change list --json`; `evidence metrics --json` | — |
| A.8.26 Application security requirements | `spec-and-design`, `secure-api-review` (OWASP API Top 10), `regulatory-controls`. | GUIDED | spec.md; review findings | Requirements quality is not machine-checked. |
| A.8.28 Secure coding | `secure-api-review`; `security-reviewer` required at T2+ (V2S-04*); secret scanning (V2K-01*). | GUIDED; ENFORCED (review ran, secrets) | audit log; `engine-tests.py` V2K-01* | No SAST shipped; wire one into CI (owner). |
| A.8.29 Security testing in development and acceptance | Review agents before push/PR (V2S-04*); pre-existing tests protected in fixes (V2G-10*); `test-strategy`; `evidence gaps` counts only ingested machine-readable passes. | ENFORCED (partial); GUIDED; OWNER ACTION (CI, DAST, pen test) | `evidence gaps`; `evidence change status` | Security testing depth is guided, not gated. |
| A.8.31 Separation of development, test and production | Agent production releases denied without human `RELEASE_APPROVAL` (V2G-06*). | ENFORCED (recognised deploy commands); OWNER ACTION (environment separation) | `engine-tests.py` V2G-06* | Detection uses a policy list of deploy tools; unknown paths are not caught. Separation of environments and credentials is yours. |
| A.8.32 Change management | As CC8.1. | ENFORCED (agent); OWNER ACTION (branch protection) | as CC8.1 | as CC8.1 |
| A.8.33 Test information | Secret scanning keeps credentials out of fixtures (V2K-01*). | OWNER ACTION (primary); ENFORCED (secrets only) | `engine-tests.py` V2K-01* | No detection of production or personal data in test data; that is policy and environment control. |

## NIST SP 800-218 SSDF v1.1

| Practice | Evidence Chain mechanism | Status | Evidence query | Gaps / owner |
| --- | --- | --- | --- | --- |
| PO.1 Define security requirements for development | Org and repo policy JSON (V2X-01*); `compliance-discovery` → `.evidence/context/compliance.md`; `regulatory-controls` control sets. | ENFORCED (policy applied); GUIDED (requirements) | policy files; compliance.md | Control-set owners are `UNASSIGNED` until named (owner action). |
| PO.2 Roles and responsibilities | Human-only approval (V2A-01*); named review agents per tier (V2S-04*); `training-matrix.md`. | ENFORCED (approval separation); OWNER ACTION (people, roles) | `approval.json`; training records | — |
| PO.3 Supporting toolchains | The five plugins, gate engine, `evidence` CLI, managed settings, CI workflow. | OWNER ACTION (deploy, enable CI, run canary); ENFORCED once live | canary; CI | Plugin hooks under `allowManagedHooksOnly` are verified per deployment by the canary, not documented by Anthropic. |
| PO.4 Criteria for software security checks | Tier Definition of Done; required review agents per tier (V2S-04*); `evidence gaps`. | ENFORCED (agents ran, stages); GUIDED (criteria) | `evidence metrics --json`; `evidence gaps` | — |
| PO.5 Secure development environments | Managed settings (permission denies, sandbox); control plane (V2G-09*); secret scanning (V2K-01*); dangerous git config (V2K-02*). | ENFORCED (in-session); OWNER ACTION (deploy settings, network allowlist, endpoint hardening) | `engine-tests.py`; canary | Workstation security is yours. |
| PS.1 Protect all forms of code | Protected-ref pushes and agent merges denied (V2G-05*); control plane (V2G-09*). | ENFORCED (agent); OWNER ACTION (branch protection, host access, commit signing) | `engine-tests.py` V2G-05* | No commit signing is enforced. |
| PS.2 Release integrity verification | Plugin versions and version-bump CI check (for this repo's plugins only). | OWNER ACTION | CI | No artifact signing, checksums or provenance (SLSA/SBOM) is produced for your releases. |
| PS.3 Archive and protect each release | `release-readiness` skill and `evidence-package` assemble release evidence. | OWNER ACTION (largely); GUIDED | release evidence package | Archiving and protecting releases and their provenance is your release system's job. |
| PW.1 Design to meet security requirements | `spec-and-design`, `architect` ADRs, `secure-api-review` threat model; T3 requires intent + spec + plan (V2G-04*). | GUIDED; ENFORCED (artifacts exist) | spec.md; `.evidence/decisions/` | — |
| PW.2 Review the design | Human approval bound to the plan sha256; any plan edit voids it (V2A-01*). | ENFORCED (approval); GUIDED (`architect`) | `approval.json` | Approval proves someone approved, not how carefully (see spot-audit in `baseline-metrics.md`). |
| PW.4 Reuse well-secured software | `codebase-cartographer` before new modules; dependency review in `secure-api-review`. | GUIDED; OWNER ACTION (dependency vetting, SCA) | review findings | No dependency allowlist or SCA. |
| PW.5 Secure coding practices | `secure-api-review`; secret scanning (V2K-01*). | GUIDED; ENFORCED (secrets) | `engine-tests.py` V2K-01* | — |
| PW.6 Build configuration | CI/build files are gated source needing a change ticket and ≥ T2 (V2G-08*, V2S-02*). | ENFORCED (agent edits); OWNER ACTION (compiler/build hardening) | `engine-tests.py` V2G-08* | Build hardening content is not checked. |
| PW.7 Review code | Required review agents per tier before push/PR (V2S-04*); `code-reviewer` runs `REVIEW.md` passes at T3. | ENFORCED (runs recorded); GUIDED (findings); OWNER ACTION (human code-owner review) | audit log `agent-completed`; `evidence change status` | No SAST shipped. |
| PW.8 Test executable code | Pre-existing tests protected in fixes (V2G-10*); `verifier` required (V2S-04*); `evidence gaps` counts only ingested JUnit/eval passes. | ENFORCED (partial); GUIDED; OWNER ACTION (CI) | `evidence gaps`; CI | Test adequacy is guided. |
| PW.9 Secure-by-default settings | `secure-api-review` guidance for product configuration. | GUIDED | review findings | Not checked mechanically. |
| RV.1 Identify vulnerabilities continuously | `security-reviewer` per change; `SECURITY.md` reporting route for this project. | GUIDED; OWNER ACTION (scanning, disclosure programme for your product) | review findings | No continuous scanning shipped. |
| RV.2 Assess, prioritise, remediate | `evidence change start --kind fix`; failing-test first, then pre-existing tests protected (V2G-10*); `deviation-capa-runbook.md`. | ENFORCED (fix flow); GUIDED | `evidence change status <KEY> --json` | Prioritisation is human. |
| RV.3 Analyse root causes | `root-cause-analysis` skill; CAPA requires a permanent eval or an engine case. | GUIDED | CAPA records; new eval / engine cases | — |

## Keeping this honest

When a mechanism changes, update the row and its cited cases in the same change. A row
may say ENFORCED only if a labelled case in `engine-tests.py` proves it and that case
passes; otherwise it says GUIDED or OWNER ACTION.
