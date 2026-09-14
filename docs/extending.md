# Extending Evidence Chain

This is the "how do I actually add something" reference. `CONTRIBUTING.md` covers
philosophy and review priorities; this covers the mechanics of adding a skill, a hook,
or a plugin, grounded in files that already exist in this repository. Read
`CONTRIBUTING.md` first — the standards there (discovery-first, no stack-specific
assumptions, fail closed, no score-based gates) apply to everything below.

Every field and pattern named here was confirmed against real files in this repo as of
this writing, not inferred from general Claude Code documentation. Where this repo's own
git history changed its mind about something, that history is cited.

---

## 1. Adding a new skill

### Directory structure

```
plugins/<plugin-name>/skills/<skill-name>/SKILL.md
```

Confirmed against, among others:

- `plugins/evidence-sdlc/skills/root-cause-analysis/SKILL.md`
- `plugins/evidence-sdlc/skills/schema-migration/SKILL.md`
- `plugins/evidence-discovery/skills/stack-discovery/SKILL.md`

Every one of the 23 `SKILL.md` files in this repo lives at exactly this depth: plugin,
then `skills/`, then a directory named after the skill, then `SKILL.md`. There is no
observed variant (no skills with supporting files alongside `SKILL.md`, no nested
skill directories) except `stack-discovery`, which references
`${CLAUDE_PLUGIN_ROOT}/templates/` for output templates — so a skill *can* ship
supporting files under its plugin's root, referenced via `${CLAUDE_PLUGIN_ROOT}`, but the
skill's own instructions still live in one `SKILL.md`.

### Frontmatter

Checked the YAML frontmatter of all 23 `SKILL.md` files in the repo: every single one
uses exactly two fields, `name` and `description`, and no others (no `allowed-tools`, no
`model`, no custom fields). Don't add extra frontmatter fields on the assumption they're
supported here — none of the existing skills do.

```yaml
---
name: schema-migration
description: Design and review data-model migrations safely — expand/contract phasing, backfill verification, tested rollback, and the regulated-record integrity checks a normal code review misses. Use whenever anyone says "migration", "alter the schema", "add a column", "change the data model", "backfill", "rename a field", "drop a table", "reindex", and on any edit under a migrations directory. ...
---
```

`name` matches the directory name (`schema-migration` skill lives in
`skills/schema-migration/`).

**`description` is the one field that matters most, and CONTRIBUTING.md is explicit
about the standard it must meet:**

> Skill descriptions state both what the skill does **and** the contexts that should
> trigger it. Under-triggering is the common failure — be explicit and slightly pushy.

In practice, every description in this repo does two things in one paragraph:

1. States what the skill does, in a sentence.
2. Lists concrete trigger phrases and situations — often as a literal quoted list of
   things a user might say — plus any structural triggers (e.g. "on any edit under a
   migrations directory").

Look at `root-cause-analysis`'s description as the pattern to copy: it says what the
skill is for ("Trace a defect to its actual root cause from evidence, rather than
proposing a plausible-sounding fix"), then lists the exact phrases that should trigger it
("this is broken", "why is this failing", "debug this", "investigate this error",
"production issue", "it works locally but not in X", pastes a stack trace, reports any
unexpected behaviour). `stack-discovery`'s description goes further and explicitly says
to trigger "even when CLAUDE.md, a README, an architecture document, or another document
appears to already answer it" — anticipating the failure mode where an agent thinks it
already has the answer and skips the skill. When you write a new skill's description,
enumerate the actual phrases someone would type, not a paraphrase of the topic, and name
the specific situations (file patterns, commands, states) that should trigger it even
when it's not obvious the skill applies.

### Body conventions

There is no single mandated body template — headings vary a lot across the 23 files —
but two patterns recur enough to be worth following rather than inventing your own
structure:

- **Named, numbered "Rule" sections.** `schema-migration` uses `## Rule 0 — expand-contract
  is the default`, `## Rule — the backward-compatibility window`, `## Rule — backfill
  verification`, etc. `stack-discovery` uses `## Rule 0 — documentation is a claim, not
  evidence` through `## Rule 4 — record uncertainty explicitly`. The pattern is either
  `## Rule N — <short name>` or `## Rule — <short name>`, each rule self-contained enough
  to be cited by name from another skill (e.g. `root-cause-analysis` explicitly borrows
  `stack-discovery`'s "ask only for what is essential and missing" rule by name rather
  than re-stating it).
- **A closing section that tells the agent what "done" looks like.** This is common but
  *not* universal or fixed to one heading — across the corpus the closing section is
  most often `## Output` (used in `root-cause-analysis`, `schema-migration`, and others)
  or `## Done means`, but several skills close with something specific to their own
  content instead (`## Boundaries`, `## Never`, `## Rollback is a tested path`). Don't
  assume `## Output` is a required heading; do make sure your skill ends with *something*
  that pins down the deliverable or exit criteria, because that's what every skill in
  this repo does even when the heading text differs. `root-cause-analysis` closes with a
  literal Markdown table template under `## Output format`; `schema-migration` closes
  with `## Output` as an ordered checklist of what a migration proposal must state.

Other conventions worth carrying over, seen repeatedly:
- Skills reference other skills and hooks by exact name in prose (e.g.
  "`protect-validated-paths` gates a `migrations/` directory and stops there"), so a
  reader can find the referenced file. Don't describe another skill's behaviour without
  naming it.
- Skills that write files name the exact path and say to commit it (`stack-discovery`:
  "Write `.evidence/context/stack.md` and `.evidence/context/deployment.md` from the
  templates in `${CLAUDE_PLUGIN_ROOT}/templates/`. Commit them.").
- Per CONTRIBUTING.md, skills must not hardcode a stack, framework, or language — if a
  skill needs that kind of fact, it reads `.evidence/context/` (written by
  `stack-discovery`) or asks. A skill that hardcodes this will be declined per
  CONTRIBUTING.md's explicit "What to avoid" list.
- CONTRIBUTING.md also says: "Prefer editing an existing skill over adding a new one. The
  number of skills is a cost." Adding a new skill directory should be the exception, not
  the default extension mechanism.

### Agent frontmatter

Agents (`plugins/*/agents/*.md`) are a distinct file kind from `SKILL.md` — they carry a
`tools:` field skills never do — so the "exactly two fields" rule above does not describe
them. As of this writing, 5 of the 7 agents in this repo use exactly `name`, `description`
and `tools`: `stack-surveyor`, `flake-triage`, `test-designer`, `security-reviewer`,
`compliance-reviewer`. Two — `codebase-cartographer` and `verifier` — also carry
`model: haiku`.

That split is deliberate, not partial coverage waiting to be finished. The two tiered
agents are mechanical and low-stakes if occasionally imprecise: `codebase-cartographer`
is explicitly told to over-include when unsure and its output is sanity-checked by a
human during planning immediately after; `verifier` pastes real command output verbatim
for a human to read, so a misjudgement doesn't silently propagate. The other five each
state, in their own file, why getting them wrong is expensive: `stack-surveyor` exists
because "confidently wrong is the expensive failure mode"; `flake-triage` classifies "the
most valuable and most commonly misclassified outcome"; `test-designer` derives the case
set everything downstream trusts; `security-reviewer` and `compliance-reviewer` are named
directly in `governance/continuity-and-cost.md`'s model-tiering guidance ("design,
planning, the council, and compliance review go to a capable [model]"). Do not add
`model: haiku` to any of those five on the assumption the split was accidental — read the
reasoning above first, and add a comparably specific reason if you believe a particular
agent should move tiers.

`model:` accepts an alias (`haiku`/`sonnet`/`opus`/`inherit`) — use the alias, not a
dated full model ID, so the pin doesn't go stale as model names change. This is the only
frontmatter field beyond `name`/`description`/`tools` that appears anywhere in this
repo's agents; no `color` or other field is used.

---

## 2. The `hooks.json` schema

Confirmed against all three hook manifests that exist in this repo:
`plugins/evidence-discovery/hooks/hooks.json`, `plugins/evidence-quality/hooks/hooks.json`,
`plugins/evidence-sdlc/hooks/hooks.json`, plus the scripts they invoke, including
`plugins/evidence-sdlc/scripts/gate-plan-exists.sh` and (note: the actual path is under
`evidence-quality`, not `evidence-sdlc`) `plugins/evidence-quality/scripts/require-issue-key.sh`.

### Shape

```json
{
  "description": "...",
  "hooks": {
    "<EventName>": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "if": "Bash(git commit *)",
            "command": "bash",
            "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/require-issue-key.sh"],
            "statusMessage": "Checking tracker key",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

Top level: a `description` string for the whole file, and a `hooks` object keyed by
event name. Every event name actually used in this repo: `PreToolUse`, `PostToolUse`,
`SessionStart`. Each event maps to an array of matcher groups; each group has an
optional `matcher` and a `hooks` array of individual hook entries.

Fields observed on individual hook entries, and what each does here:

- **`type`** — always `"command"` in this repo. Every hook entry across all three files
  uses it; no other type is exercised.
- **`matcher`** — restricts which tool call the group applies to. Observed values:
  `"Bash"` (evidence-quality's commit gate, evidence-sdlc's push/deploy gates) and
  `"Edit|Write|MultiEdit"` (evidence-sdlc's plan/protected-path/test-weakening gates and
  its audit-log `PostToolUse` hook). `SessionStart` groups in this repo omit `matcher`
  entirely — it fires unconditionally at session start.
- **`if`** — a further condition evaluated only on top of a matching tool call, written
  as a tool-call pattern string, e.g. `"Bash(git commit *)"` or `"Bash(*deploy*)"`. Used
  to narrow a `Bash` matcher down to a specific command shape without writing that logic
  into the shell script itself. Not every hook entry has one — `gate-plan-exists.sh`'s
  entry has no `if` because its `matcher` (`Edit|Write|MultiEdit`) is already the whole
  condition; the script itself does the finer-grained path filtering.
- **`command`** — the executable to spawn. In every hook in this repo, it's the literal
  string `"bash"` — see the exec-form section below for why this is a hard requirement,
  not a style choice.
- **`args`** — an array of arguments passed to `command`. In every hook in this repo it's
  a single-element array holding the script path, always written with the
  `${CLAUDE_PLUGIN_ROOT}` placeholder so the path resolves correctly regardless of where
  the plugin is installed, e.g. `["${CLAUDE_PLUGIN_ROOT}/scripts/gate-plan-exists.sh"]`.
- **`statusMessage`** — a short human-readable string shown while the hook runs, e.g.
  `"Checking for an approved plan.md"`. Present on most gating hooks; absent on the two
  `SessionStart` context-only hooks in `evidence-quality` and on the `PostToolUse`
  audit-log hook (which is `async`, see below) and on `require-repo-profile.sh` in
  evidence-discovery — i.e. it's used where a human is waiting on a decision, and
  skipped where the hook is just gathering context.
- **`timeout`** — seconds before the hook is killed. Observed values are `15` (fast
  deterministic checks: plan gate, protected-path gate, test-weakening gate, branch
  protection, deploy gate, tracker-key gate) and `20` (checks that touch more, like
  `preflight.sh`, `session-context.sh`, `require-repo-profile.sh`,
  `check-test-plan-rows.sh`). No hook in this repo omits `timeout` except the
  `async` audit-log hook.
- **`async`** — set `true` on exactly one hook in the repo: `evidence-sdlc`'s
  `PostToolUse` `audit-log.sh` entry. It has neither `timeout` nor `statusMessage`,
  consistent with being fire-and-forget logging rather than a gate a session waits on.

### Exec form vs. shell form — the single most important thing to get right

This is not a style preference; it is a documented distinction in Claude Code's own
hook execution mechanism, and getting it wrong took down every hook in this repository
in production, twice, in the same day.

**The rule:** if a hook entry has an `args` field at all — even `"args": []` — Claude
Code selects **exec form**: it spawns `command` directly via `posix_spawn` as one literal
executable name, with **no shell involved and no word-splitting**. If `args` is absent,
Claude Code selects **shell form**: `command` is parsed as a full shell command line.

**What that means concretely:**
- `"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh"]` — exec form,
  correct. `bash` is spawned as a literal executable name (found on `PATH`), and the
  script path is passed as its own `argv` element.
- `"command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh", "args": []` — exec form
  (because `args` is present), and **broken**: Claude Code tries to spawn a single
  executable literally named `bash /path/to/foo.sh` (with an embedded space), which does
  not exist as a file, so it fails with `ENOENT`.
- `"command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh"` with no `args` key at all —
  shell form, and this one *would* work, because the whole string gets parsed as a shell
  command line and word-split normally. The bug only exists when `args` is present
  alongside a multi-word `command` string.

**The incident, from this repo's own git history:**

1. `afcfbd6` ("PILOT-3: Stop hooks from failing open when a gate script isn't
   executable") found a real problem: Claude Code's plugin zip loses the executable bit
   on extraction, and a hook script without its exec bit was being executed directly and
   failing with `EACCES` — which the runtime treats as **allow**, so a broken gate fails
   *open* rather than blocking. The fix committed was to invoke every script via
   `bash ${CLAUDE_PLUGIN_ROOT}/scripts/foo.sh` instead of executing it directly, so the
   exec bit stops mattering. But every hook entry still carried `"args": []` from before,
   which nobody removed.
2. `c984a86` ("PILOT-16: Fix live-breaking regression from PILOT-3's bash-wrapper fix")
   is the direct consequence: because `args` was still present, every single hook in the
   marketplace (all 9 entries across the three `hooks.json` files) started failing with
   `ENOENT: no such file or directory, posix_spawn 'bash /Users/.../scripts/session-context.sh'`
   — exactly the class of silent failure PILOT-3 was trying to eliminate, now hitting
   everyone. The commit message is explicit about why this shipped broken: "this shipped
   broken in PILOT-3 because that fix was never actually run through Claude Code's own
   hook runtime before being committed — only the underlying scripts were tested by
   direct shell invocation, which does not exercise the hooks.json `command`/`args`
   contract at all." The fix was to split `command` and `args` back into the correct
   exec-form shape shown above, across all 9 entries.
3. `a74af63` ("Fix evidence doctor's hooks.json check for the exec-form command/args
   shape") is the follow-on: the repo's own `evidence doctor` CLI validator
   (`cli/evidence`) had a `_iter_hook_commands` helper that only ever looked at the
   `command` string to resolve a hook's script path. Once PILOT-16 changed every entry to
   `command: "bash"` with the script in `args`, the validator started reporting `bash`
   itself as a missing script for all 9 entries — a clean tool went red the moment the
   real bug was fixed. The fix made the validator resolve the script path from `args`
   when `args` is present (exec form) and from the `command` string when it's absent
   (shell form), matching the actual documented semantics instead of assuming one shape.

**The lesson stated explicitly in the PILOT-16 commit message, worth repeating verbatim
for anyone adding a new hook:** "shell-testing the target script is not sufficient
evidence that the hooks.json entry pointing at it is correct." Running
`bash scripts/foo.sh` by hand and seeing it work proves nothing about whether the
`command`/`args` shape in `hooks.json` will actually invoke it — that only exercises the
script, never the `hooks.json` contract. Test a new hook by triggering it through Claude
Code itself (a real `SessionStart`, a real matching tool call), not just by running the
script directly.

**Practical rule for a new hook in this repo:** always write it as
`"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/<your-script>.sh"]` — never
put the interpreter and path together in one `command` string while also supplying
`args`.

---

## 3. `plugin.json` and `marketplace.json` conventions

Read in full: `plugins/evidence-sdlc/.claude-plugin/plugin.json` and
`.claude-plugin/marketplace.json`, plus the other four plugins' `plugin.json` files for
consistency.

### `plugin.json`

```json
{
  "name": "evidence-sdlc",
  "description": "The Evidence Chain control plane: skills that encode our standards, subagents that verify work, and hooks that make the non-negotiable gates deterministic.",
  "author": {
    "name": "Suparn Bector",
    "email": "suparnbector@gmail.com"
  }
}
```

Every one of the 5 `plugins/*/.claude-plugin/plugin.json` files in this repo uses
exactly this shape: `name` (matches the plugin's directory name), `description` (a
prose summary, one sentence, of what the plugin's skills/hooks/subagents collectively
do), and an `author` object with `name` and `email`. No plugin in this repo has any
other top-level field.

**The one rule this repo has already learned the hard way, stated explicitly in
CONTRIBUTING.md:**

> **Never add a `version` field to a `plugins/*/.claude-plugin/plugin.json`.** This was
> tried twice and reverted twice. A static version string makes `/plugin update`
> silently no-op on every real change that doesn't also bump that string — the install
> just quietly stays on stale, possibly-buggy code. Per Anthropic's own
> plugin-marketplace documentation and the version strategy their own official plugins
> use, omitting `version` lets Claude Code track the resolved git commit SHA instead,
> which updates correctly on every commit with nothing to remember. This holds for a
> `directory`-sourced marketplace exactly as it does for a git-hosted one — the source
> type doesn't change the mechanics.

Do not re-derive a justification for adding `version` back — cite the rule above; it's
already been tried and reverted twice per CONTRIBUTING.md.

### `marketplace.json`

```json
{
  "name": "evidence-chain",
  "owner": {
    "name": "Suparn Bector",
    "email": "suparnbector@gmail.com"
  },
  "plugins": [
    {
      "name": "evidence-discovery",
      "source": "./plugins/evidence-discovery",
      "description": "..."
    }
  ]
}
```

The single `.claude-plugin/marketplace.json` at the repo root has `name`, an `owner`
object (`name`/`email`), and a `plugins` array with one entry per plugin directory. Each
entry repeats `name` (matching the plugin's own `plugin.json` `name` and its directory),
a `source` as a relative `./plugins/<name>` path (this marketplace is directory-sourced,
not git-hosted — per CONTRIBUTING.md's version rule, that doesn't change the no-`version`
rule), and its own `description` — which in every observed case matches the plugin's own
`plugin.json` description verbatim. When adding a new plugin, add its entry here with the
same `name` and the same `description` string used in its own `plugin.json`, and never
add `version` to either file.

---

## Summary checklist for a new skill or gate

- Skill: `plugins/<plugin>/skills/<skill-name>/SKILL.md`, frontmatter is exactly `name`
  + `description`, description states what it does and lists concrete trigger phrases
  and situations (be explicit and slightly pushy, per CONTRIBUTING.md), body uses named
  `## Rule` sections where it helps and ends with a clear statement of the deliverable
  or done-criteria (heading text varies — `## Output` and `## Done means` are common, not
  mandatory). No stack-specific assumptions; read `.evidence/context/` or ask instead.
- Hook: add an entry under the right event (`PreToolUse`, `PostToolUse`, or
  `SessionStart`) in the plugin's `hooks/hooks.json`, always as
  `"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/<script>.sh"]` (exec form —
  never combine `bash <path>` into one `command` string while `args` is present), add
  `statusMessage` when a human is waiting on the decision, set `timeout` (15 for a fast
  deterministic check, 20 for something heavier), and use `async: true` only for
  fire-and-forget work like logging. Make the script fail **closed** and explain the
  block, per CONTRIBUTING.md. Test it by actually triggering it through Claude Code, not
  just by running the script by hand.
- New plugin: `plugin.json` with only `name`, `description`, `author` — never `version`
  — plus a matching entry in the root `.claude-plugin/marketplace.json` with the same
  `name` and `description` and a `./plugins/<name>` `source`.
