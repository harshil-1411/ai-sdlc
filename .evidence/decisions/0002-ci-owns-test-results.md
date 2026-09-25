# 0002. CI's signed results are the proof; nobody commits result files

Status: Proposed (revision 2, PILOT-60 design, 2026-09-25). Revision 1 (PILOT-58) was deferred after its design review found two defects; this revision adopts both fixes: the self-check exemption is hard-coded in the trusted CLI, and CI signs only the freshly downloaded artifact.
Date: 2026-09-24 (revision 2: 2026-09-25)
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-58, PILOT-60   Spec: intent/2026-09-25-usability/spec.md (REQ-USA-01..04)
Supersedes: none
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- `scripts/ci/run-tests.sh` writes JUnit to `validation/results/`, which is committed and change-controlled (`**/validation/**`).
- `tests/content_acceptance_tests.py` runs `evidence gaps --strict` (REQ-V2C-09) *inside* the
  content suite, before that suite writes its own fresh `content.xml`. So a requirement
  proven only by the content suite can never pass the same run's self-check.
- PILOT-54, PILOT-57 and PILOT-58 each needed the maintainer to run the tests twice locally and commit
  `validation/results`. Agents cannot, because `validation/` is change-controlled.
- CI's `sign-and-gate` job downloads the checks job's results **into `validation/results/` in its checkout**, signs `validation/results/*.xml` with the base branch's CLI, and runs `gaps --strict` (`.github/workflows/ci.yml:82–105`). Files a PR commits to that directory are signed too. The adopter template `pipelines/github-actions/evidence-chain.yml` has the same shape with `test-results/`.
- Revision 1 let `adapter.yml` name the self-check requirement (`self_check_requirement`). The adapter is agent-editable, so it could exempt any requirement from the gate.

## Decision
1. **The self-check is the last step of `run-tests.sh`.** After every suite, it runs `evidence gaps --strict --self-check --only-results --results "$out"` against the results that run just wrote, and writes its outcome as the JUnit case for REQ-V2C-09 (`self-check.xml`). REQ-V2C-09 stops being a content-suite check.
   - `--self-check` exempts exactly one ID, the constant `SELF_CHECK_REQUIREMENT = "REQ-V2C-09"` in the trusted CLI. No adapter or policy key can name or change it.
   - The authoritative run in `sign-and-gate` never passes `--self-check`.
2. **Results directory.** `run-tests.sh` takes `EVIDENCE_RESULTS_DIR`. Local runs default to a directory outside the working tree (`${TMPDIR:-/tmp}/evidence-chain-results/<repo>-<hash>`), so no session in that folder sees a change, and the script prints it.
3. **CI signs only the fresh artifact.**
   - `checks` writes to `${{ runner.temp }}/results` and uploads it.
   - `sign-and-gate` downloads it to `${{ runner.temp }}/results`, signs the files there with the base branch's CLI, and runs `gaps --strict --only-results --results` on that directory. It never signs or reads `validation/results/` in the checkout.
   - `gaps --only-results` ignores the adapter's `test_results_location`.
   - The adopter templates under `pipelines/` do the same. The GitLab template, whose artifacts must live in the project directory, fails when the results directory is tracked by git.
4. **`validation/results/` in the repository becomes historical.** It is kept for past
   evidence, but no change is required to update it. The traceability gate that decides a
   merge is `sign-and-gate`'s, run on signed CI results.

## Consequences
- Easier:
  - no manual result commits, and one local run is enough;
  - a human's local test run no longer causes integrity violations in a concurrent
    session;
  - agents can run the whole `run-tests.sh`.
- Harder: a local `evidence gaps --strict` without `--results <dir>` reads only the
  historical files, and may report UNVERIFIED for new requirements. Docs and the script's last line say to pass the
  local results directory.
- Constrained:
  - CI must keep uploading results as an artifact for `sign-and-gate`;
  - `.github/workflows/ci.yml` is change-controlled, so a human applies its part;
  - for the one PR whose base CLI predates `--only-results`, the `sign-and-gate` step feature-detects the flag and falls back to the 2.1.0 command on the downloaded directory (or the human applies the `ci.yml` part after merge; the maintainer chooses at plan approval).
- Cost to reverse: low; set `EVIDENCE_RESULTS_DIR=validation/results` locally.
- Review trigger: reopen if a customer's audit needs the result files in the repository,
  rather than in signed CI artifacts.

## Alternatives
| Option | Why it lost |
| --- | --- |
| The content suite ingests its own fresh results before REQ-V2C-09 | Still one ordering-sensitive test inside a suite; local runs still write into the working tree |
| Let agents write `validation/results` when the plan claims it | Weakens change control on validation assets; result files by an agent are self-assertion |
| Keep committing results (status quo) | A manual round trip on every change; stale committed results can mask or fake proof |
| Name the self-check requirement in `adapter.yml` (revision 1) | The adapter is agent-editable: it could exempt any requirement |
| Keep downloading into `validation/results/` and delete tracked files first | Relies on a cleanup step in the job that holds the key; a separate directory is simpler to reason about |
