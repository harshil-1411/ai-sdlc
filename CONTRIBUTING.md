# Contributing

Thanks for considering it. This project is a set of conventions as much as code, so the
most valuable contributions are usually about **what works in practice**, not features.

For the mechanics of adding a new skill, understanding the `hooks.json` exec-form vs.
shell-form schema, or the `plugin.json`/`marketplace.json` conventions referenced below,
see [`docs/extending.md`](docs/extending.md).

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
- **Never add a `version` field to a `plugins/*/.claude-plugin/plugin.json`.** This was
  tried twice and reverted twice, here, in this repo: a static version string made
  `/plugin update` silently no-op on a real change that didn't also bump that
  string — the install just quietly stayed on stale, possibly-buggy code (see
  `PILOT-13`/`PILOT-15`). Not every official Anthropic plugin follows this
  convention — some do set a `version` — so don't cite "what official plugins do"
  as the justification; cite this repo's own reverted-twice history instead.
  Omitting `version` lets Claude Code track the resolved git commit SHA instead,
  which updates correctly on every commit with nothing to remember. This holds
  for a `directory`-sourced marketplace exactly as it does for a git-hosted one —
  the source type doesn't change the mechanics.

## Code of conduct

Be decent. Assume good faith. Disagree about the substance, not the person.
