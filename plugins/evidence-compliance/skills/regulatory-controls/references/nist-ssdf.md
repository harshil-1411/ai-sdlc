# NIST SSDF — Secure Software Development Framework (SP 800-218 v1.1)

> Scope: the SSDF practices, grouped as Prepare the Organization (PO), Protect the
> Software (PS), Produce Well-Secured Software (PW) and Respond to Vulnerabilities (RV).
> Often a contractual obligation for software sold to US federal agencies (via the
> secure software development attestation). Not covered: the individual tasks under each
> practice (e.g. PW.4.1) — cite tasks in findings where useful — and the organisational
> practices that no single change can evidence. Source: drafted from the public
> publication; practice names follow v1.1.
> Owner: UNASSIGNED — the adopting organisation must assign a named owner before relying on this set (evidence doctor warns while unassigned).
> Last reviewed: never by an adopter; drafted 2026-09-24. **Not an authoritative interpretation.**

## Controls

PO practices are mostly organisational; for them, "what to check in a change" is whether
the change used the defined requirement, role, toolchain and environment rather than
bypassing them.

| ID | Control | What to check in a change | Typical evidence |
| --- | --- | --- | --- |
| SSDF-PO.1 | Define Security Requirements for Software Development | The change's spec draws its security requirements from the organisation's defined set, including those for third-party components | Spec security section citing the standard |
| SSDF-PO.2 | Implement Roles and Responsibilities | Author, reviewer and approver are distinct named people with the defined roles | PR review and approval record |
| SSDF-PO.3 | Implement Supporting Toolchains | The change went through the standard CI toolchain (build, scans, tests); no manual or out-of-band build | CI run for the commit |
| SSDF-PO.4 | Define and Use Criteria for Software Security Checks | The defined gate criteria (scan thresholds, required checks) were applied and the result recorded | Required-check config, gate result |
| SSDF-PO.5 | Implement and Maintain Secure Environments for Software Development | Build and development environments are not weakened (CI secrets scoped, runners hardened, no new broad credentials) | CI config diff, secret scoping |
| SSDF-PS.1 | Protect All Forms of Code from Unauthorized Access and Tampering | Repository access controlled, branch protection in force, commits attributable (signed where required) | Branch protection config, commit signature check |
| SSDF-PS.2 | Provide a Mechanism for Verifying Software Release Integrity | Release artifacts carry checksums or signatures and provenance consumers can verify | Signature/provenance attestation |
| SSDF-PS.3 | Archive and Protect Each Software Release | Each release is archived with its provenance data (including SBOM) and protected from alteration | Release archive, SBOM |
| SSDF-PW.1 | Design Software to Meet Security Requirements and Mitigate Security Risks | Design addresses the security requirements and identified risks; threat model updated for new trust boundaries | Spec design section, threat model |
| SSDF-PW.2 | Review the Software Design to Verify Compliance with Security Requirements and Risk Information | Design was reviewed against the requirements before implementation | Spec review/approval record |
| SSDF-PW.3 | (Withdrawn in v1.1 — content moved into PW.4) (paraphrased) | Record as N/A; assess third-party component checks under PW.4 | — |
| SSDF-PW.4 | Reuse Existing, Well-Secured Software When Feasible Instead of Duplicating Functionality | New dependencies are vetted (maintenance, known vulnerabilities, licence, provenance); no hand-rolled replacement of a well-secured library (especially crypto) | Dependency review, SCA report, SBOM diff |
| SSDF-PW.5 | Create Source Code by Adhering to Secure Coding Practices | Input validation, output encoding, safe error handling, no hard-coded secrets | Review record, secret-scan result |
| SSDF-PW.6 | Configure the Compilation, Interpreter, and Build Processes to Improve Executable Security | Security-relevant compiler/build/interpreter settings not weakened; build is reproducible from the pipeline | Build config diff |
| SSDF-PW.7 | Review and/or Analyze Human-Readable Code to Identify Vulnerabilities and Verify Compliance with Security Requirements | Code review and static analysis ran on the change; findings resolved or justified | SAST report, PR review |
| SSDF-PW.8 | Test Executable Code to Identify Vulnerabilities and Verify Compliance with Security Requirements | Security tests (and DAST/fuzzing where the risk warrants) ran against the changed behaviour | Security test results in CI |
| SSDF-PW.9 | Configure Software to Have Secure Settings by Default | New settings and features ship secure by default; insecure options require explicit opt-in and are documented | Default config diff, test of defaults |
| SSDF-RV.1 | Identify and Confirm Vulnerabilities on an Ongoing Basis | The changed components are covered by continuous scanning and a vulnerability intake path | Scan schedule, disclosure policy |
| SSDF-RV.2 | Assess, Prioritize, and Remediate Vulnerabilities | A vulnerability fix is risk-assessed, prioritised within policy, and has a regression test | Triage record, fix PR, regression test |
| SSDF-RV.3 | Analyze Vulnerabilities to Identify Their Root Causes | Fixes for vulnerabilities record a root cause and whether the same class exists elsewhere | RCA record linked to the fix |

## Blocking classes

Any **Not met** on SSDF-PS.1, SSDF-PW.4 (an unvetted dependency with a known-exploitable
vulnerability), SSDF-PW.5 (a hard-coded secret), SSDF-PW.7 or SSDF-PW.8. For a release,
also SSDF-PS.2 and SSDF-PS.3.

## Common misses

- **Attestation without artifacts.** Signing a secure-development attestation commits the
  organisation to these practices; an SBOM or provenance record that is not produced per
  release leaves the attestation unsupported.
- A vulnerability fixed without a root cause (RV.3), so the same class recurs in the
  next module.
- New dependencies added in a "small" change without the vetting PW.4 expects, because
  the review focused on the code, not the lockfile.
- CI credentials broadened to make a pipeline work, weakening PO.5 without anyone
  recording it.
