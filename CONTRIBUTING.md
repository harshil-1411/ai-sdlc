# Contributing

Thanks for considering it. This project is a set of conventions as much as code, so the
most valuable contributions are usually about **what works in practice**, not features.

## What is especially welcome

- **Reports from real rollouts.** What broke, what people routed around, what you had to
  loosen. Negative results are more useful here than success stories.
- **Gates that failed open.** If a hook silently did not fire in your environment, that
  is the highest-priority class of bug in this repo.
- **Regulatory review.** If you work in quality or regulatory affairs and something in
  `plugins/evidence-compliance/` or `governance/` is wrong, misleading, or would not
  survive an audit, please say so specifically.
- **Portability fixes.** Shell scripts that assume GNU tools, macOS-only behaviour,
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

- Skill descriptions state both what the skill does **and** the contexts that should
  trigger it. Under-triggering is the common failure — be explicit and slightly pushy.
- Hook scripts must fail **closed** for anything that enforces a policy, and must
  explain the block in a way that tells the user how to proceed legitimately.
- Every JSON file must parse. Every shell script must pass `bash -n`.
- Prefer editing an existing skill over adding a new one. The number of skills is a cost.

## Code of conduct

Be decent. Assume good faith. Disagree about the substance, not the person.
