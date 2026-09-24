---
name: stack-discovery
description: Determine a repository's actual technology and deployment stack from the code and write .evidence/context/stack.md and deployment.md. Use on the first session in a repo, when .evidence/context/ is missing or stale, and on any question about languages, runtimes, frameworks, datastores, build tooling or deployment targets ("what stack", "what framework", "what database", "what does this repo use") — even when a README seems to answer it. Ask when evidence is ambiguous.
---

# Stack discovery

**No skill in this framework hardcodes a stack.** Most organisations have repositories of
different ages and shapes. A skill that assumes a framework will be confidently wrong
in half of them, and confidently wrong is the expensive failure mode.

Discovery runs once per repository, writes a profile, and everything downstream reads
the profile. Re-run it when the stack changes.

## Rule 0 — documentation is a claim, not evidence

Never answer a question about this repository's stack from CLAUDE.md, a README,
an architecture document, or any other prose. Those record what someone intended
or once built. A declared dependency is not a used one — check for actual imports.
If documentation and code disagree, the code wins and the disagreement is itself
a finding worth reporting.

## Do not offer — run

Do not ask "would you like me to run discovery?". If a stack question is asked
and no profile exists, run the survey and answer from its results.

## Rule 1 — evidence, then question, never guess

Every line you write must be traceable to a file you read. If you cannot establish
something from evidence, you **stop and ask**. Do not fill a gap with the most common
answer. Write the question, get the answer from a human, record who answered.

Ambiguity that must always be escalated rather than guessed:
- Two frameworks present (a migration in progress, or a genuine split)
- A lockfile that disagrees with the manifest
- Infrastructure code that does not match what is actually deployed
- A test framework present with no tests, or tests with no runner config
- Any environment or region you find referenced but cannot confirm exists

## Ask only for what is essential and missing

Ask only for information that is (a) genuinely absent from the repository and
(b) would change what you produce. If an answer would not change the output,
do not ask for it.

Batch questions into one round where possible rather than interrogating turn by
turn. Order them most-consequential first. A question you could have answered by
reading a file is a question you should not have asked.

## Rule 2 — read in this order

1. **Manifests and lockfiles** — whatever the repo has: `package.json`, `pom.xml`,
   `build.gradle`, `requirements.txt`/`pyproject.toml`, `go.mod`, `*.csproj`,
   `Gemfile`, `composer.json`, `Cargo.toml`. The lockfile is the truth; the manifest
   is the intent.
2. **Runtime pins** — `.nvmrc`, `.tool-versions`, `.python-version`, Dockerfile base
   images, CI image declarations.
3. **Entry points and layout** — what actually starts, and how the tree is organised.
4. **Data layer** — ORM config, migration directories, schema files, connection
   string shapes (never the credentials).
5. **Build and task runner** — `Makefile`, npm scripts, gradle tasks, whatever exists.
   Identify the single command for build, test, lint, run.
6. **Test frameworks** — unit, integration, end-to-end, each with where its tests live.
7. **Deployment** — IaC (CDK / Terraform / CloudFormation / SAM / Helm / Serverless),
   container definitions, pipeline files, environment configuration, regions.
8. **Observability** — logging, metrics, tracing libraries in use.
9. **Version control conventions** — branch naming, commit message patterns from
   `git log`, PR templates, CODEOWNERS.

## Rule 3 — separate "declared" from "in use"

A dependency in a manifest is not proof it is used. Grep for actual imports. Record
both: `declared` and `evidence of use`. Dead dependencies matter for the upgrade and
supply-chain conversations later.

## Rule 4 — record uncertainty explicitly

Every entry gets a confidence marker:
- `[confirmed]` — read it in a file, cite the file
- `[inferred]` — strong evidence but not declarative, say what the evidence was
- `[ASK]` — could not establish; the question is written out and waiting for a human

A profile containing `[ASK]` lines is incomplete. Downstream skills must treat an
`[ASK]` in an area they depend on as a blocker, not a detail.

## Output

Write `.evidence/context/stack.md` and `.evidence/context/deployment.md` from the
templates in `${CLAUDE_PLUGIN_ROOT}/templates/`. Commit them. They are reviewed like
code and they are the input to every plan.

Finish by presenting the `[ASK]` list to the human as numbered questions, most
consequential first. Do not proceed to any spec or plan while an `[ASK]` blocks it.
