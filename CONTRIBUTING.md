# Contributing

Thanks for considering it. This project is a set of conventions as much as code, so the
most valuable contributions are usually about **what works in practice**, not features.

For the mechanics of adding a skill, an agent, a gate rule or a plugin, see
[`docs/extending.md`](docs/extending.md).

## What is especially welcome

- **Reports from real rollouts.** What broke, what people routed around, what you had to
  loosen. Negative results are more useful here than success stories.
- **Gates that failed open.** If a hook silently did not fire in your environment, that
  is the highest-priority class of bug in this repo.
- **Regulatory review.** If you work in quality or regulatory affairs and something in
  `plugins/evidence-compliance/` or `governance/` is wrong, misleading, or would not
  survive an audit, please say so specifically.
- **Bypasses.** Any tool call shape that gets past a gate the docs say it can't. Send
  it with the exact command (see SECURITY.md for anything exploitable).
- **Portability fixes.** Python 3.8 compatibility, macOS-only or GNU-only behaviour,
  Windows gaps.
- **Adapting notes** for stacks, trackers, or test tools not yet covered.

## What to avoid

- **Do not add stack-specific assumptions to skills.** The discovery-first design is the
  core idea of this project. If a skill needs to know a framework, it reads
  `.evidence/context/`, or it asks. A pull request that hardcodes a language, framework,
  or deployment target will be declined on principle.
- **Do not add gates that block on generated scores.** Human approval informed by
  findings is the control; an automatically-counted threshold gets gamed.
- **Do not soften a control with an exception clause** to make it convenient. If a
  control needs an exception, that is a signal the control is wrong, not that it needs a
  caveat.

## Standards for a change

- A skill description states what the skill does **and** when to use it, including
  the literal phrases people type, in about three sentences
  ([docs/extending.md](docs/extending.md#frontmatter)).
- Anything that enforces a policy lives in the gate engine
  (`plugins/evidence-sdlc/scripts/engine/`), not in a new hook script. It fails
  **closed**, and its deny message says how to proceed legitimately. The way forward
  must be a human action, never a switch the agent can flip. Every rule has labelled
  cases in `engine-tests.py`.
- Prefer editing an existing skill over adding a new one. Every skill has a cost.

## Validation standard

Run all of these before opening a PR. CI (`.github/workflows/ci.yml`) runs the same
set:

```
python3 -m py_compile plugins/evidence-sdlc/scripts/engine/*.py plugins/evidence-sdlc/scripts/cli/*.py plugins/evidence-quality/scripts/*.py
for f in $(git ls-files '*.sh'); do bash -n "$f" || echo "FAIL $f"; done
for f in $(git ls-files '*.json' | grep -v /evals/results/); do python3 -m json.tool "$f" >/dev/null || echo "FAIL $f"; done
python3 plugins/evidence-sdlc/scripts/tests/engine-tests.py
python3 plugins/evidence-sdlc/scripts/tests/cli-lifecycle-tests.py
bash plugins/evidence-sdlc/scripts/tests/template-sensor-tests.sh
bash cli/tests/test_cli_fixtures.sh
bash scripts/ci/check-version-bump.sh origin/main
claude plugin validate .
```

Or run every suite at once with `bash scripts/ci/run-tests.sh` (one run is enough). It writes
JUnit and logs to `EVIDENCE_RESULTS_DIR`, by default a directory outside the working tree that it
prints, and nothing under version control. Its last step is this repository's own
`evidence gaps --strict --self-check --only-results` over that run's results (REQ-V2C-09). To check
traceability locally afterwards, pass that directory: `evidence gaps --strict --results <dir>`.
Never commit test results: CI's signed artifact is the evidence (ADR-0002).

For a fast subset of the engine suite, `engine-tests.py --suite NAME` (repeatable) runs only the
named suite functions, and `-k SUBSTR` reports only the matching cases while every other case still
runs its hook call, so outcomes match a full run. A `-k` that selects nothing exits 1 with
`0 cases matched`; an unknown suite exits 2.

A hook change must also be tested **through Claude Code itself**: start a session,
confirm the `Evidence Chain gates live` canary line, and trigger one deny. Running a
script by hand doesn't exercise the `hooks.json` contract. See
[docs/extending.md](docs/extending.md#exec-form-vs-shell-form-the-one-thing-to-get-right)
for the incident that taught this.

## Releases and versions

**Every `plugins/*/.claude-plugin/plugin.json` has a semver `version`**, and the
matching entry in `.claude-plugin/marketplace.json` carries the same version. All five
plugins are currently versioned together.

- **Any change to a plugin's files needs a version bump** in both files. That covers
  skills, agents, commands, hooks, the engine, policy and templates. Changes to
  `evals/results/` and eval `SUMMARY.md` files are exempt.
  `scripts/ci/check-version-bump.sh` compares each plugin against the base branch and
  fails CI if files changed but the version didn't.
- Use patch for fixes and wording, minor for a new skill, agent, command or policy key,
  and major for anything that denies something it didn't before, or that changes the
  approval or state format.
- **Add a `CHANGELOG.md` entry** under the new version. Mark breaking gate changes as
  such.

**Why the version field came back.** v1 omitted `version` on purpose. It was added and
reverted twice (PILOT-13, PILOT-15), because a static version string made
`/plugin update` silently no-op on a real change that didn't also bump the string. The
install quietly stayed on stale, possibly buggy code. Omitting `version` made Claude
Code track the git commit instead. That fixed updates, but left installs with no
release identity, no changelog anchor, and nothing for an auditor or a managed rollout
to pin. v2 keeps the version and closes the original failure mechanically: CI refuses
a plugin change without a bump, so the stale-`/plugin update` problem can't recur
unnoticed. Don't remove the check to get a PR through. Bump the version.

## Code of conduct

Be decent. Assume good faith. Disagree about the substance, not the person.
