# Extending Evidence Chain

This is the "how do I actually add something" reference: a skill, an agent, a gate
rule, a hook or a plugin. [CONTRIBUTING.md](../CONTRIBUTING.md) covers the
philosophy, the release process and the validation standard. Read it first. Its
standards apply to everything below: discovery-first, no stack-specific assumptions,
fail closed, no score-based gates.

---

## 1. Adding a skill

### Layout

```
plugins/<plugin>/skills/<skill-name>/SKILL.md
plugins/<plugin>/skills/<skill-name>/references/*.md     (optional, loaded on demand)
```

There are 30 `SKILL.md` files. Supporting material either sits in the skill's own
`references/` directory (for example `regulatory-controls/references/` and
`e2e-ui-testing/references/`, which is loaded only for the tool the profile names), or
is shared at the plugin root and referenced with `${CLAUDE_PLUGIN_ROOT}/templates/…`.

### Frontmatter

All 30 skills use exactly two fields, `name` (which must equal the directory name)
and `description`. Don't add others.

The `description` is what decides whether the skill fires. It does two things in one
paragraph:

1. It says what the skill does, in one sentence.
2. It says when to use it, including the literal phrases people type ("this is
   broken", "what stack", "add a column") and structural triggers ("on any edit under
   a migrations directory").

v2 trimmed every description to that shape. Long lists of near-duplicate phrases
diluted the trigger space for the other 29 skills. Keep new descriptions to about
three sentences. Put the rest in the body.

### Body conventions

- Use named rules (`## Rule N — <name>`) that other skills can cite by name.
- End with a section that pins down the deliverable (`## Output`, `## Done means` or
  similar).
- Refer to other skills, agents and the engine by exact name.
- Name the exact paths a skill writes to, and tell it to commit them.
- Never hardcode a stack. Read `.evidence/context/` or ask.
- Prefer editing an existing skill to adding a new one. Every skill has a cost.

### Eval coverage

A new skill isn't Done until its plugin's `evals/` directory has cases for it: at
least a `trigger` case and a `non-trigger` case, plus a `behavior` case for any rule
that isn't obvious. Each case is a directory holding `prompt.md`, `case.yaml` and an
optional `graders/`, run with `claude plugin eval`. The engine's sensor flags a new
`SKILL.md` that has no `<skill>-*` eval directory.

---

## 2. Adding an agent

There are 11 agents: 7 in `evidence-sdlc` (codebase-cartographer, architect,
security-reviewer, code-reviewer, verifier, release-manager, docs-writer),
`stack-surveyor` in `evidence-discovery`, `test-designer` and `flake-triage` in
`evidence-quality`, and `compliance-reviewer` in `evidence-compliance`. See
[skills-reference.md](skills-reference.md#agents).

### Frontmatter

| Field | Use |
| --- | --- |
| `name`, `description` | Required. The description says when the main session should dispatch the agent |
| `tools` | Required in this repo. Give the least the job needs. A reviewer gets `Read, Grep, Glob`, plus `Bash` only if it must run something |
| `model` | Optional. Use an alias (`haiku`, `sonnet`, `opus`, `inherit`), never a dated ID. Only `codebase-cartographer` pins one (`haiku`): its output is explicitly over-inclusive and a human checks it during planning straight away. `verifier` was pinned to Haiku in v1. That pin was removed in v2, because the verifier's verdict gates push, so a cheap misjudgement would propagate |
| `permissionMode`, `maxTurns` | Supported by Claude Code for plugin agents. None of the shipped agents sets them yet. `maxTurns` is a reasonable bound for a long-running reviewer. Don't use `permissionMode` to loosen anything: the engine denies Tier 3 edits in auto-accept modes whatever the agent's mode is |

### Least privilege is enforced, not just declared

The engine reads `agent_type` from each hook payload. A write by any agent on the
policy's `read_only_agents` list is denied, whatever its `tools` field says. So when
you add an agent:

- If it's read-only, add its name to `read_only_agents` in
  `plugins/evidence-sdlc/policy/default-policy.json`, and add an engine test.
- If it must write, like `docs-writer`, limit it to the paths it needs. Its writes
  still go through every gate: active change, claims, control plane and secrets.
- If it's a required reviewer, add it to `required_agents` for the relevant tiers. Its
  completed runs are recorded automatically by the PostToolUse hook on `Agent`/`Task`.

Add an eval case for the new agent under its plugin's `evals/`.

---

## 3. Adding or changing a gate rule

Every gate is part of the one engine. **Don't add a new hook script.** A gate rule has
three parts, and a change isn't complete without all three:

1. **Policy.** If the rule needs data (paths, refs, patterns, a flag), add a key to
   `plugins/evidence-sdlc/policy/default-policy.json`. Decide how a repository layer
   may affect it: list keys that should only grow go in `TIGHTEN_UNION` in
   `engine/state.py`, and strictness booleans go in `TIGHTEN_OR`. Any key in neither
   set is ignored in a repo policy. Document the key in
   [policy-reference.md](policy-reference.md).
2. **Engine rule.** Implement it in `engine/evidence_policy.py`:
   - A path rule goes in `check_write` or `check_gated`.
   - A command rule goes in `check_bash`, `_check_git`, `_check_gh` or `_check_deploy`.
   - New command shapes go in `cmdparse.py`.
   - Return `deny("<rule-id>", "<reason>")`. The reason must say what was denied, why,
     and the legitimate way forward, and that way forward must be one a human takes,
     not a switch the agent can flip.
   - Anything the engine can't parse must deny, not allow.
3. **Regression cases** in `plugins/evidence-sdlc/scripts/tests/engine-tests.py`. Label
   each case with its requirement ID (`"V2G-05 push HEAD:main denied"`). Include:
   - the deny case;
   - the allow case, so the rule doesn't over-block;
   - every bypass shape you can think of: wrappers, `bash -c`, absolute paths,
     case changes, `..` traversal.

Then run the validation standard in CONTRIBUTING.md, and add a row to
[gates-reference.md](gates-reference.md).

**Never add a bypass environment variable the agent could set.** The three human-only
variables (`CHANGE_TICKET`, `RELEASE_APPROVAL`, `EVIDENCE_ACTIVE_CHANGE`) are safe only
because settings files are control plane. A new override needs the same protection,
or it becomes a hole.

---

## 4. The `hooks.json` schema

All three manifests (`evidence-discovery`, `evidence-sdlc`, `evidence-quality`) use
the same shape:

```json
{
  "description": "…",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash|Agent|Task",
        "hooks": [
          {
            "type": "command",
            "command": "bash",
            "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/engine/hook.sh", "pre"],
            "statusMessage": "Evidence Chain gates",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

The events in use are `PreToolUse`, `PostToolUse`, `UserPromptSubmit` and
`SessionStart`. v2 dropped the `if` filters: every Bash call reaches the engine,
because a glob such as `Bash(git commit *)` misses `git -C . commit` and `env git
commit`.

### Exec form vs shell form: the one thing to get right

If a hook entry has an `args` field at all, even `[]`, Claude Code uses **exec form**.
It spawns `command` as one literal executable name, with no shell and no word
splitting. Without `args`, it uses **shell form**.

- `"command": "bash", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/x.sh", "pre"]` is
  correct.
- `"command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/x.sh", "args": []` is **broken**. It
  looks for an executable literally named `bash /path/x.sh` and fails with `ENOENT`.
  The runtime treats a hook that fails to execute as **allow**.

This took down every hook in the repository at once. `afcfbd6` (PILOT-3) wrapped
scripts in `bash …` to survive a lost execute bit, but left `"args": []` in place.
`c984a86` (PILOT-16) fixed it. The lesson from that commit still holds: *"shell-testing
the target script is not sufficient evidence that the hooks.json entry pointing at it
is correct."* Test a hook change through Claude Code itself. The session-start canary
(`Evidence Chain gates live`) plus one deliberate denial is the minimum.

Always invoke through `bash`, never rely on the file's execute bit, and use
`${CLAUDE_PLUGIN_ROOT}` for plugin paths. Managed hooks, which don't have
`${CLAUDE_PLUGIN_ROOT}`, use a fixed install path instead
([managed-hooks.example.json](managed-hooks.example.json)).

---

## 5. `plugin.json` and `marketplace.json`

```json
{
  "name": "evidence-sdlc",
  "version": "2.0.0",
  "description": "…",
  "author": { "name": "…", "email": "…" },
  "homepage": "https://github.com/<owner>/evidence-chain#readme",
  "repository": "https://github.com/<owner>/evidence-chain",
  "license": "MIT",
  "keywords": ["…"]
}
```

- **`version` is required, and must be bumped whenever the plugin's files change.**
  `scripts/ci/check-version-bump.sh` fails CI otherwise. See CONTRIBUTING.md for why
  v1 had no version field and why v2 has one.
- **Don't add a `dependencies` field.** When a declared dependency isn't installed,
  the plugin's skills stop loading entirely (the v2 eval run caught this: no
  evidence-sdlc skill fired in any case until the field was removed). Treat sibling
  plugins as soft dependencies: skills say what's missing, and `evidence doctor`
  reports which siblings are installed.
- **`homepage` and `repository`** point at the published repository,
  `https://github.com/harshil-1411/ai-sdlc` (plus `#readme` for `homepage`). A fork
  changes both to its own remote.

The root `.claude-plugin/marketplace.json` has one entry per plugin, with the same
`name`, a `./plugins/<name>` `source`, the same `description` and the same `version`
as the plugin's own `plugin.json`. Keep them identical, and bump both together.

Validate with `claude plugin validate .` from the repository root.

---

## Checklist

- **Skill:** `SKILL.md` with `name` and `description` only; a what-plus-when
  description of about three sentences; eval cases; a row in skills-reference.
- **Agent:** least-privilege `tools`; added to `read_only_agents` if it's read-only,
  and to `required_agents` if it gates push; an eval case; a row in
  skills-reference.
- **Gate rule:** policy key, engine rule and labelled engine-tests cases; rows in
  policy-reference and gates-reference; fails closed; only a human can get past it.
- **Any plugin change:** version bump, a CHANGELOG.md entry, and the validation
  standard in CONTRIBUTING.md.
