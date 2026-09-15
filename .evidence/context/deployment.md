# Repository profile — deployment stack

Repo: evidence-chain   Established: 2026-09-10

## Infrastructure as code
- [confirmed] None. No Terraform, CDK, CloudFormation, SAM, Helm, or Serverless files found anywhere in the tree.
- [inferred] This repo has no infrastructure of its own to provision — it distributes Claude Code plugins via the marketplace mechanism, not a running service.

## Runtime services
| Service | Purpose | Defined in | Confidence |
| --- | --- | --- | --- |
| — | none — no deployed runtime service | — | [confirmed] |

## Environments
| Environment | Account/Project | Region(s) | Who can deploy | Agent autonomy tier |
| --- | --- | --- | --- | --- |
| dev | n/a | n/a | n/a | n/a |
| staging/UAT | n/a | n/a | n/a | n/a |
| validation | n/a | n/a | n/a | n/a |
| production | n/a | n/a | n/a | n/a |

- [inferred] These rows describe a consuming application's environments, not evidence-chain's. This repo's only "environment" is the Claude Code plugin marketplace itself: `.claude-plugin/marketplace.json` at the repo root, installed per-user via `/plugin install`.

## Data residency
- [confirmed] Not applicable — no data store, no regions in use.

## Pipelines
- [confirmed] CI system: none configured in this repo. `pipeline.example.yml` at the repo root is explicitly a reference template ("Continuous integration and continuous testing — reference shape... Translate to whatever CI system deployment.md says you actually use"), not an active pipeline — it is designed to be copied into a *consuming* repo.
- [confirmed] No `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, or other CI config found in evidence-chain itself.
- [ASK] Given CONTRIBUTING.md's requirement that JSON parse and shell scripts pass `bash -n`, is there an intended CI pipeline for evidence-chain's own repo (distinct from `pipeline.example.yml`, which is a deliverable for other repos), or is validation expected to stay manual? — awaiting: maintainer

## Rollback
- [confirmed] No deployment mechanism, so no rollback mechanism applies to this repo directly.
- [inferred] Plugin-level "rollback" is `/plugin uninstall <name>@evidence-chain` or pinning an older marketplace commit, per standard Claude Code plugin marketplace behaviour — not documented explicitly in this repo.
- [ASK] Last rehearsed: never (no prior releases beyond the initial import commit). — awaiting: maintainer, once a versioning/release process for the marketplace itself is defined

## Open questions — [ASK]
1. Is a CI pipeline planned for evidence-chain's own repo to enforce CONTRIBUTING.md's JSON/`bash -n` validation standard, or is that intentionally left manual? — awaiting: maintainer
2. What is the release/versioning process when a plugin's `version` in `plugin.json` changes (e.g. tagging, changelog, marketplace re-publish) — none is documented yet. — awaiting: maintainer
