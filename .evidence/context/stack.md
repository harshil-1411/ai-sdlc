# Repository profile — technology stack

Repo: evidence-chain   Established: 2026-09-10   By: suparn.bector@msbdocs.com   Re-verify: on stack change

Every line carries evidence and one of [confirmed] / [inferred] / [ASK].

## Languages and runtimes
- [confirmed] Bash, no version pin found — 10 scripts under `plugins/*/scripts/*.sh`, all `#!/bin/bash` (portable shebang, not `#!/usr/bin/env bash`)
- [confirmed] Markdown — 64 files: skill instructions (`plugins/*/skills/*/SKILL.md`), agent definitions (`plugins/*/agents/*.md`), templates (`plugins/*/templates/*.md`), docs, governance
- [confirmed] JSON — 11 files: plugin manifests (`plugins/*/.claude-plugin/plugin.json`), hook configs (`plugins/*/hooks/hooks.json`), `.claude-plugin/marketplace.json`, `managed-settings.json`, `.claude/settings.json`
- [inferred] No compiled/application language present. This repo is the Evidence Chain framework itself — a set of Claude Code plugins (skills, agents, hooks) — not an application codebase. `evidence-discovery` is designed to run *inside* a consuming repository; run against evidence-chain itself, most of the template's application-stack sections do not apply.

## Package management
- [confirmed] None. No `package.json`, `pom.xml`, `build.gradle`, `requirements.txt`/`pyproject.toml`, `go.mod`, `*.csproj`, `Gemfile`, `composer.json`, or `Cargo.toml` found anywhere in the tree.
- [confirmed] Distribution mechanism instead is the Claude Code plugin marketplace: `.claude-plugin/marketplace.json` (created this session) lists 5 plugins, each installed via `/plugin install <name>@evidence-chain`. No lockfile concept applies.

## Frameworks and major libraries
| Library | Version | Declared in | Evidenced in use | Confidence |
| --- | --- | --- | --- | --- |
| Claude Code plugin system | n/a (`plugin.json` schema) | `plugins/*/.claude-plugin/plugin.json` | 5 plugins load skills/agents/hooks | [confirmed] |
| Claude Code hooks (PreToolUse/PostToolUse/SessionStart) | n/a | `plugins/*/hooks/hooks.json` | referenced by `evidence-sdlc`, `evidence-discovery`, `evidence-quality` | [confirmed] |
| Mermaid (diagram syntax, in docs only) | n/a | `README.md` fenced blocks | rendered in README | [confirmed] |

## Data and persistence
- [confirmed] No datastore. No ORM config, migration directory, or schema file found.
- [inferred] The framework's own "data" is the artifact chain it produces in a consuming repo: `.evidence/context/*.md`, `intent.md`, `spec.md`, `plan.md` — plain files committed to git, not a database.

## Build, test, run
| Purpose | Command | Defined in | Exits non-zero on failure |
| --- | --- | --- | --- |
| Build | — none | — | n/a |
| Unit test | — none | — | n/a |
| Integration test | — none | — | n/a |
| E2E test | — none | — | n/a |
| Lint | `bash -n <script>.sh` (per CONTRIBUTING.md, run manually) | `CONTRIBUTING.md` | yes, per `bash -n` semantics |
| Run locally | `/plugin marketplace add ./` then `/plugin install <name>@evidence-chain` inside Claude Code | `README.md` "Install" section | n/a |

- [ASK] CONTRIBUTING.md requires "Every JSON file must parse. Every shell script must pass `bash -n`" as a contribution standard, but there is no committed script or CI config that runs these checks automatically. Confirm whether this is intentionally manual (pre-commit discipline only) or whether a validation script/CI step is expected to exist. — awaiting: maintainer

## Test frameworks and locations
| Layer | Framework | Tests live in |
| --- | --- | --- |
| — | none present | — |

- [inferred] `plugins/evidence-quality` *ships* test-strategy/test-automation/testrail-authoring skills for consuming repositories, but the evidence-chain repo itself has no test suite of its own.

## Observability
- [confirmed] None built into this repo's own operation. `plugins/evidence-sdlc/scripts/audit-log.sh` writes an audit trail as a `PostToolUse` hook when the plugin is installed in a consuming repo — that is a feature the framework provides, not logging/metrics/tracing of the framework's own code.

## Version control conventions
- [inferred] Grown well past a single commit since this profile was established (2026-09-10) — `git log --oneline | wc -l` returns 68 as of 2026-09-15. The line below is stale and this whole section needs a real re-run of `stack-discovery`, not a hand-patch; corrected here only enough that this file stops asserting something git itself contradicts.
- [confirmed] Single branch: `master` (`git branch -a`) — still true as of 2026-09-15; every commit across every PILOT/TRACE/ITEM round has landed directly on `master`, no feature branches used. `README.md` and `managed-settings.json` refer to "the protected branch" generically, and `block-protected-branch-push.sh` exists but its protected-branch name is configurable, not yet exercised against a real push attempt here (no remote is configured at all — `git remote -v` is empty).
- [inferred] A real commit-message convention has emerged in practice: `EVIDENCE_ISSUE_KEY_PATTERN` in `.claude/settings.json` (`PILOT-[0-9]+|TASK2-[AB][0-9]+|TRACE-[0-9]+|ITEM-[0-9]+`) and dozens of real commit messages now follow it. This is observed practice, not a maintainer's explicit decision — the [ASK] below is not resolved by this observation alone; a named person still needs to confirm it's the intended long-term convention, per this profile's own rule that only a human answer resolves an `[ASK]`.
- [ASK] Is the `PILOT-<n>`/`TRACE-<n>`/`TASK2-<item>`/`ITEM-<n>` session-local tracker-key convention the intended long-term one for changes made *to* evidence-chain itself, or should a real tracker be provisioned? No CODEOWNERS file or PR template exists either. — awaiting: maintainer

## Open questions — [ASK]
1. No CI validation currently runs `bash -n` on the (now well over 10) shell scripts or JSON-parses the JSON files that CONTRIBUTING.md's contribution standard requires — confirm whether this is expected to be manual or should be automated. — awaiting: maintainer
2. Is `PILOT-<n>`/`TRACE-<n>`/`TASK2-<item>`/`ITEM-<n>` an acceptable long-term tracker-key convention for changes made *to* evidence-chain's own repository, or should a real tracker be provisioned before more of this framework's own history accumulates under an informal one? — awaiting: maintainer
3. This entire profile is now five days old and the repository has changed substantially (dozens of new commits, new CLI behavior, new skill/agent content) since it was established — a full re-run of `stack-discovery` (not a hand-patch like this one) is overdue. — awaiting: maintainer, or the next session that touches this repo's own discovery
