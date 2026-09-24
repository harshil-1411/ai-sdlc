# 0002. CI's signed results are the proof; nobody commits result files

Status: Proposed
Date: 2026-09-24
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-58   Spec: intent/2026-09-24-integrity-monitor-hardening/spec.md
Supersedes: none
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- `scripts/ci/run-tests.sh` writes JUnit to `validation/results/`, which is committed.
- `tests/content_acceptance_tests.py` runs `evidence gaps --strict` (REQ-V2C-09) *inside* the
  content suite, before that suite writes its own fresh `content.xml`. So a requirement
  proven only by the content suite can never pass the same run's self-check.
- PILOT-54 and PILOT-57 each needed the maintainer to run the tests twice locally and commit
  `validation/results`. Agents cannot, because `validation/` is change-controlled.
- CI's `sign-and-gate` job already downloads the checks job's fresh results, signs them with
  the key, and runs `gaps --strict` using the base branch's trusted CLI
  (`.github/workflows/ci.yml`). That is the stronger proof.

## Decision
1. **Move the self-check.** `run-tests.sh` runs `evidence gaps --strict` as its **last** step,
   against the results that run just wrote. REQ-V2C-09 stops being a content-suite check.
   Its proof becomes that final step, which writes its own JUnit case. `gaps` does not
   count REQ-V2C-09 as unproven within the run that is producing its result. The adapter
   names this with `self_check_requirement`.
2. **Configurable results directory.** `run-tests.sh` takes `EVIDENCE_RESULTS_DIR`.
   - CI sets it to `validation/results` (artifact, then signed by `sign-and-gate`).
   - Local runs default to a directory outside the working tree, so no session in that
     folder sees a change.
3. **`validation/results/` in the repository becomes historical.** It is kept for past
   evidence, but no change is required to update it. The traceability gate that decides a
   merge is `sign-and-gate`'s, run on signed CI results.

## Consequences
- Easier:
  - no manual result commits;
  - a human's local test run no longer causes integrity violations in a concurrent
    session;
  - agents can run the whole `run-tests.sh`.
- Harder: a local `evidence gaps --strict` without `--results <dir>` reads only the
  historical files, and may report UNVERIFIED for new requirements. Docs say to pass the
  local results directory.
- Constrained: CI must keep uploading results as an artifact for `sign-and-gate`.
- Cost to reverse: low; set `EVIDENCE_RESULTS_DIR=validation/results` locally.
- Review trigger: reopen if a customer's audit needs the result files in the repository,
  rather than in signed CI artifacts.

## Alternatives
| Option | Why it lost |
| --- | --- |
| The content suite ingests its own fresh results before REQ-V2C-09 | Still one ordering-sensitive test inside a suite; local runs still write into the working tree |
| Let agents write `validation/results` when the plan claims it | Weakens change control on validation assets; result files by an agent are self-assertion |
| Keep committing results (status quo) | A manual round trip on every change; stale committed results can mask or fake proof |
