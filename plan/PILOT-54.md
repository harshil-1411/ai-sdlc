# Plan: Publish metadata, CODEOWNERS, absolute-path fix for the managed-settings template
Tracker: PILOT-54   From: HANDOFF.md owner actions + 2026-09-24 key-exposure finding   Date: 2026-09-24
Risk tier: 1 — metadata, docs and tests only; no engine or hook logic changes. No policy tier floor applies (`.github/CODEOWNERS` is not under `.github/workflows/**`). The one security-relevant edit (`managed-settings.json`) is control plane and was made by the human (commit 5f5487d), not by this change's agent.

Approval is not written in this file. A human records it with `/evidence-sdlc:approve <KEY> <plan-sha>`
(or `evidence approve <KEY>` in their own terminal, or an approving review in GitHub
mode); it binds to this file's hash, so any edit after approval voids it.

Any claim below not confirmed from a file, a command, or a named person is marked
inline as [NEEDS VERIFICATION]. An unmarked claim asserts that it was checked.

## Why
- The manifests and docs still carry `REPLACE-WITH-YOUR-ORG`. The repo is published at
  https://github.com/harshil-1411/ai-sdlc (the `origin` remote). `main` branch protection requires code-owner review,
  but no `.github/CODEOWNERS` exists. So that requirement binds nothing, and PR #1 (PILOT-57) needed an admin merge.
- On 2026-09-24 the Read tool read the deployed managed-settings file and exposed the signing key.
  - Cause: a permission rule written `Read(/Library/...)` with a single leading `/` is resolved relative to the project. Absolute paths in permission rules need `//`.
  - The repo template `managed-settings.json` had the same single-slash form. The human fixed it on this branch in 5f5487d, which also set the marketplace `repo` to `harshil-1411/ai-sdlc`.
  - This change adds the regression test and corrects the docs and governance claims.
- PILOT-57 (2.0.1) made the hook perform `evidence change start|advance`. It refuses them when chained with other programs. The `start` command's instructions should say so.
- This restart replaces the first PILOT-54 attempt, whose state was written unsigned by the agent's CLI (defect D6, fixed in PILOT-57). The human deleted that state.

## Files claimed
- `plan/PILOT-54.md`
- `plugins/*/.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`
- `CHANGELOG.md`
- `README.md`
- `HANDOFF.md`
- `docs/managed-settings.md`
- `docs/extending.md`
- `governance/supplier-audit-packet.md`
- `pipelines/github-actions/evidence-chain.yml`
- `.github/CODEOWNERS`
- `tests/content_acceptance_tests.py`
- `plugins/evidence-sdlc/commands/start.md`
- `validation/results/**`

Not claimed; made by the human: `managed-settings.json` (control plane, done in 5f5487d).

## Files that change
- `plugins/{evidence-sdlc,evidence-discovery,evidence-quality,evidence-compliance,evidence-integrations}/.claude-plugin/plugin.json`:
  `homepage` → `https://github.com/harshil-1411/ai-sdlc#readme`, `repository` → `https://github.com/harshil-1411/ai-sdlc`, `version` 2.0.1 → 2.0.2.
- `.claude-plugin/marketplace.json`: all six `version` fields 2.0.1 → 2.0.2.
- `CHANGELOG.md`: new `## 2.0.2 — 2026-09-24 (PILOT-54)` entry above 2.0.1.
- `.github/CODEOWNERS` (new; `.github/` exists): adapted from `pipelines/github-actions/CODEOWNERS.example`.
  - Default owner `* @harshil-1411`.
  - The same control-plane lines: `.evidence/policy.json`, `.evidence/secrets-allowlist.json`, `.evidence/changes/`, `.claude/`, `managed-settings.json`, `.github/`.
  - Plus `plugins/evidence-sdlc/scripts/engine/` and `plugins/evidence-sdlc/policy/`.
  - Owner handle `@harshil-1411` [NEEDS VERIFICATION: the maintainer confirms at plan review, or gives another handle. It is the only account known to have write access].
- `pipelines/github-actions/evidence-chain.yml:76`: the default repo becomes `harshil-1411/ai-sdlc`.
- `README.md:61-63`: `/plugin marketplace add harshil-1411/ai-sdlc`; drop the placeholder sentence.
- `docs/extending.md:213`: state the real `homepage`/`repository` values instead of the placeholder note.
- `docs/managed-settings.md`:
  - In "Signing key" step 3, add that absolute paths in `permissions` rules must start with `//` (a single `/` is project-relative).
  - Add a canary step: ask the agent to Read a nonexistent file inside the managed directory. The expected result is "denied by your permission settings", not "file not found".
  - Tick the "Publish the marketplace" owner action.
- `governance/supplier-audit-packet.md:36-38`: qualify "the sandboxed agent shell cannot [read the key]".
  - Add that the Read tool is also denied, by permission rules with `//` paths and by the engine's Read hook.
  - Add that the 2.0.0 template's single-slash rules did not deny it.
- `HANDOFF.md:97-104`:
  - Mark the placeholder and branch-protection owner actions done (2026-09-24).
  - Add the `//` finding under gotchas.
  - Add PILOT-57's lesson: run review agents one at a time.
- `plugins/evidence-sdlc/commands/start.md` steps 2–3:
  - Create the branch first, in its own Bash call.
  - Then run `evidence change start` as its own command. The gate engine performs it, and refuses it when chained.
- `tests/content_acceptance_tests.py`: new checks (see Proof).

## Order of work
1. **Done by the human (5f5487d):** the `//` permission paths and the marketplace `repo` in `managed-settings.json`.
2. Add the regression checks to `tests/content_acceptance_tests.py`. REQ-P54-04 checks the current template, and also checks that the template at 1391408 (before 5f5487d, read with `git show`) **fails** the same rule. The test thus proves it detects the bug.
3. Replace placeholders in the manifests, pipeline, README and extending.md; bump versions; add the CHANGELOG entry. (Independent of 4–5.)
4. Add `.github/CODEOWNERS`. (Independent.)
5. Docs: managed-settings.md, supplier-audit-packet.md, HANDOFF.md, commands/start.md. (Independent.)
6. Run the engine, lifecycle and content suites directly (no JUNIT_OUT; `validation/` is change-controlled for the agent), `bash scripts/ci/check-version-bump.sh origin/main`, and the verifier agent (Tier 1). Commit with `PILOT-54` and the `Agent-Session` trailer. Push.
7. **Human:**
   - Every PILOT-54 requirement is proven by the content suite. Its self-check (REQ-V2C-09) reads the committed `content.xml` before the suite writes a fresh one (fix tracked for PILOT-58).
   - So in your terminal, on this branch: run `bash scripts/ci/run-tests.sh` twice, then commit and push `validation/results`.
   - Open the PR (`gh` cannot reach GitHub from the agent sandbox). A human merges.

## Mid-flight checkpoint (Tier 2/3)
N/A — Tier 1

## Reuse decisions
- CODEOWNERS is derived from the shipped `pipelines/github-actions/CODEOWNERS.example`, not written fresh.
- The new checks go in the existing `tests/content_acceptance_tests.py`, next to the managed-settings checks (lines 189–193). The version check reuses `scripts/ci/check-version-bump.sh`.

## Risks
- A wrong CODEOWNERS handle makes every PR unmergeable under the "code-owner review" protection. Rollback: revert the file (admin bypass is available; `enforce_admins=false`).
- Separation of duties: if `@harshil-1411` is both the pusher and the sole code owner, GitHub will not count an author's own review. The code owner must review from a different account, or merges keep needing the admin override.
- Rollback for everything else: `git revert`. It is metadata, docs and tests only.

## Proof

| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| REQ-P54-01 No `REPLACE-WITH-YOUR-ORG` in tracked files outside `CHANGELOG.md`, `intent/`, `plan/` and `validation/`; every plugin.json `repository` is `https://github.com/harshil-1411/ai-sdlc` | content | yes | — | `tests/content_acceptance_tests.py` "REQ-P54-01 …" | validation/results/content.xml |
| REQ-P54-02 `.github/CODEOWNERS` exists, has a default owner, covers `.evidence/policy.json`, `.claude/`, `managed-settings.json`, `.github/` and the engine, and has no `@your-org` placeholder | content | yes | — | `tests/content_acceptance_tests.py` "REQ-P54-02 …" | validation/results/content.xml |
| REQ-P54-03 Every plugin.json version equals its marketplace.json entry, is 2.0.2, and CHANGELOG has `## 2.0.2` | content + CI script | yes | — | `tests/content_acceptance_tests.py` "REQ-P54-03 …"; `scripts/ci/check-version-bump.sh` | validation/results/content.xml; CI log |
| REQ-P54-04 Every `permissions` rule in `managed-settings.json` whose path is absolute uses `//`, and the pre-fix template at 1391408 is detected as failing | content | yes | — | `tests/content_acceptance_tests.py` "REQ-P54-04 …" | validation/results/content.xml |
| REQ-P54-05 `docs/managed-settings.md` documents the `//` rule and a Read-tool canary step; the supplier packet no longer claims shell-only hiding | content | yes | — | `tests/content_acceptance_tests.py` "REQ-P54-05 …" | validation/results/content.xml |
| REQ-P54-06 `commands/start.md` says to run `evidence change start` as its own command, performed by the gate engine | content | yes | — | `tests/content_acceptance_tests.py` "REQ-P54-06 …" | validation/results/content.xml |
| REQ-P54-04 (live) With the fixed settings deployed, a Read of a file in the managed directory is denied by permission settings | manual | no | MAN-P54-01 | — | Observed denied on 2026-09-24 in session 1e01f04e ("File is in a directory that is denied by your permission settings"); the human confirmed the installed file uses `//` paths. |

## Considered and rejected
- **Editing `managed-settings.json` from the agent.** It is control plane; the engine denies it by design.
- **Fixing the content self-check ordering in `run-tests.sh` here.** It is a real defect, but it concerns the test harness and belongs with PILOT-58's harness items. The human step 7 is the existing working path.
- **Renaming the repo to `evidence-chain` to match the old placeholder.** The owner chose `harshil-1411/ai-sdlc`.
- **Bumping to 2.1.0.** No behaviour change; a patch bump is accurate.
