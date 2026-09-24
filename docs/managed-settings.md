# Managed settings: deploying Evidence Chain to an organisation

Installing the plugins gives one engineer the gates. **Managed settings** give them to
everyone, in a form engineers can't override. This page covers deploying the template,
proving the gates actually run (the canary), what to do if they don't, and the
actions only the owner can take.

The template is [`managed-settings.json`](../managed-settings.json) at the repo root.
Check every key against the
[Claude Code settings reference](https://code.claude.com/docs/en/settings-reference)
for the version you run.

## What the template does

| Block | Effect |
| --- | --- |
| `permissions.deny` / `allow` | Replaces a blanket `Bash(git *)` with narrow allows: status, diff, log, branch, switch, add, commit, fetch, rev-parse, `evidence change/gaps/doctor/scan`, and build/test/lint. It adds explicit denies for `git -c`, `git --config-env`, `git config`, `git show :path`, force and mirror pushes, `gh pr merge`, `gh api`, `curl`, `wget`, and reading `.env`, keys and certificates. `disableBypassPermissionsMode` is on |
| `allowManagedPermissionRulesOnly` | Only these permission rules apply. User and project rules are ignored |
| `enabledPlugins` | Force-enables all five `…@evidence-chain` plugins |
| `env` | OTel: `CLAUDE_CODE_ENABLE_TELEMETRY=1`, OTLP metrics and logs exporters, gRPC, and a **placeholder** `OTEL_EXPORTER_OTLP_ENDPOINT`. `OTEL_LOG_USER_PROMPTS=0` keeps prompt text out of telemetry |
| `sandbox` | Enabled, fails if unavailable, no unsandboxed commands. Network is limited to **placeholder** domains, and `~/.ssh`, `~/.aws/credentials`, `~/.config/gh`, `GITHUB_TOKEN` and `GH_TOKEN` are hidden |
| `allowManagedHooksOnly` | Only managed hooks run, plus hooks from plugins force-enabled in `enabledPlugins` (see below) |
| `disableSideloadFlags`, `allowManagedMcpServersOnly` | No side-loaded plugins or unmanaged MCP servers |
| `strictKnownMarketplaces` | A **placeholder** allowlist of marketplace sources |
| `requiredMinimumVersion` | The oldest Claude Code version allowed to start |

The engine's permission layer and the gate engine overlap on purpose. The permission
rules stop the obvious forms of an action before the hook even runs. The engine
catches the forms a glob can't see, such as `git -C x push origin HEAD:main`,
`env git …` and `bash -c "…"`.

## Deploying it

1. **Take the owner actions** [below](#owner-actions-checklist) first. The template
   doesn't work with its placeholders in place.
2. **Put the file** where Claude Code reads managed settings. You can use MDM or the
   Claude admin console (server-managed settings), or drop the file directly:
   - macOS: `/Library/Application Support/ClaudeCode/managed-settings.json`
   - Linux/WSL: `/etc/claude-code/managed-settings.json`
   - Windows: `C:\Program Files\ClaudeCode\managed-settings.json`

   The file must be root- or admin-owned, and engineers must not be able to write it.
   The engine also treats both directories as control plane, so an agent can't write
   them either.
3. **Deploy the org policy** (optional, recommended) as `evidence-policy.json` in the
   same directory. See [policy-reference.md](policy-reference.md). This is where
   GitHub approval mode, approver allowlists, change-ticket and release-approval
   patterns, and extra tier floors go.
4. **Make the marketplace known.** `strictKnownMarketplaces` only restricts which
   marketplaces can be added; it doesn't register one. To register it for everyone,
   add the same source under `extraKnownMarketplaces` in the same file:

   ```json
   "extraKnownMarketplaces": {
     "evidence-chain": { "source": { "source": "github", "repo": "acme/evidence-chain" } }
   }
   ```
5. **Run the canary** on at least one machine per OS and per Claude Code version you
   support.

## The canary

Every session the engine runs in starts with a SessionStart context line that begins:

```
Evidence Chain gates live (engine 2.0.0; policy: default + …).
```

**If that line isn't there, assume no gate is running.** This is how to test it:

1. In a **fresh session**, in a git repository on a branch with **no tracker key**
   (for example a new repo on `main` with one commit), ask:
   *"What did the Evidence Chain session-start context say?"* The answer must quote
   "Evidence Chain gates live". For the raw hook output, run `claude --debug` and look
   for the SessionStart hook.
2. In the same session, ask Claude to **create `src/x.py`** containing `print(1)`. It
   **must be denied**, with a message starting *"Writing src/x.py needs an active
   change, and none was found (branch main carries no tracker key)…"*.
3. Ask Claude to run `echo 1 > src/y.py` in Bash. It must also be denied, with the
   same message prefixed `[via Bash: redirect]`.

`evidence doctor` runs a related check, "gate engine live canary". It feeds the
shipped engine two writes in a throwaway repo and expects the source write to be
denied and the docs write allowed. That proves the engine code works on this machine
(python3, files, policy). It does **not** prove Claude Code is calling the engine, so
steps 1–3 are still needed after every deployment.

If step 1 passes but step 2 doesn't, stop and report it: a gate that says it's live but
doesn't deny is the worst possible failure. If both fail, the hooks aren't running. Go
to the next section.

The preflight line (`Preflight OK: python 3.x and the gate engine are in place`) comes
from the same plugin. If it says `PREFLIGHT FAILED`, fix `python3` first.

## `allowManagedHooksOnly` and plugin hooks

The engine ships as a **plugin** hook, and `allowManagedHooksOnly: true` blocks plugin
hooks. The current Claude Code hooks documentation says:

> Your user, project, local, and plugin hooks are blocked. Hooks from plugins
> force-enabled in managed settings `enabledPlugins` are exempt.

The template force-enables all five plugins, so on a current Claude Code the engine
should run. We still don't rely on that, for three reasons:

- the exemption isn't stated for every older version that `requiredMinimumVersion`
  allows;
- a plugin id that doesn't exactly match what's installed (for example a different
  marketplace name) isn't "force-enabled", and its hooks are silently blocked;
- the runtime treats a hook that fails to execute as **allow**, so a broken hook looks
  exactly like a quiet one.

The canary is the proof. Run it after every deployment and every Claude Code upgrade.

### Fallback: deploy the engine as managed hooks

If the canary fails and the plugin ids are correct, run the engine as **managed** hooks,
which `allowManagedHooksOnly` always permits:

1. Install this repository at `/opt/evidence-chain` (or change the paths), owned by
   root and read-only for engineers. Only `plugins/evidence-sdlc/` is required.
   Update it on the same cadence as the plugins.
2. Merge the `hooks` block of [`managed-hooks.example.json`](managed-hooks.example.json)
   into `managed-settings.json`. It registers the same events and matchers as
   `plugins/evidence-sdlc/hooks/hooks.json`, pointed at the fixed path:
   - PreToolUse on `Edit|Write|MultiEdit|NotebookEdit|Bash|Agent|Task`, calling
     `bash /opt/evidence-chain/plugins/evidence-sdlc/scripts/engine/hook.sh pre`
   - PostToolUse on the same matcher, calling `hook.sh post`
   - UserPromptSubmit, calling `hook.sh prompt` (this is what records approvals)
   - SessionStart, calling `preflight.sh`, then `hook.sh session-start`
3. Keep the plugins force-enabled for their skills, agents, commands and the `evidence`
   CLI. If `evidence` isn't on `PATH` in sessions, engineers can run
   `/opt/evidence-chain/plugins/evidence-sdlc/bin/evidence`.
4. Re-run the canary.

Don't deploy the managed hooks **and** have working plugin hooks at the same time.
Every event would then run twice, and each tool call would be logged twice in the audit
log. The denials themselves would still be correct.

A managed-hooks deployment also resists a user-level `"disableAllHooks": true`. The
settings documentation says only a managed-level `disableAllHooks` can disable managed
hooks.

## Signing key: from detected to enforced

The gate engine and the agent's shell run as the same OS user, so without a secret
the agent could, with enough effort, write a record the engine would accept. The fix
is a key the hooks can read and the agent's commands cannot:

1. Generate a 32+ character secret in your secret store.
2. Deliver it as `EVIDENCE_SIGNING_KEY` in the managed-settings `env` (the template has
   a placeholder). Hooks run outside the sandbox and see it.
3. Keep it from the agent: the template adds `EVIDENCE_SIGNING_KEY` to
   `sandbox.credentials.envVars` (deny), denies the sandbox and the Read tool access to
   the managed-settings directories, and denies `env`/`printenv`.
4. Give CI the same key as a protected secret so it can sign test results
   (`evidence results sign`) and verify approvals.

With the key in place, approvals, audit entries, integrity snapshots and CI results
are HMAC-signed, and anything unsigned or altered is rejected: a forged
`approval.json` no longer unlocks edits, a forged `agent-completed` entry no longer
satisfies the review gate, and an unsigned results file no longer proves a
requirement. Without it, sessions start with an **UNSIGNED MODE** warning and those
records are *detected* (the integrity monitor) but not *proven*.

The key only helps if the sandbox is actually on. `sandbox.failIfUnavailable: true` in
the template makes sure it is.

## Owner actions checklist

A plugin can't do any of these. Each one is the owner's job, and each should be
recorded with a name and a date.

- [ ] **Publish the marketplace.** Push this repository to a git remote. Replace
      `REPLACE-WITH-YOUR-ORG` in every `plugin.json` `homepage` and `repository`.
- [ ] **Set `strictKnownMarketplaces`** to the exact source you published. For GitHub:
      ```json
      "strictKnownMarketplaces": [ { "source": "github", "repo": "acme/evidence-chain" } ]
      ```
      For another git host: `{ "source": "url", "url": "https://git.acme.internal/platform/evidence-chain.git" }`
      (the URL must match exactly), or `{ "source": "hostPattern", "hostPattern": "^git\\.acme\\.internal$" }`.
      For a filesystem install at `/opt/evidence-chain`:
      `{ "source": "pathPattern", "pathPattern": "^/opt/evidence-chain$" }`.
      Include the official Anthropic marketplace
      (`{ "source": "github", "repo": "anthropics/claude-plugins-official" }`) only if
      you allow `security-guidance` and similar. Add the same source under
      `extraKnownMarketplaces`.
- [ ] **Set the OTel endpoint.** Replace `OTEL_EXPORTER_OTLP_ENDPOINT` with your
      collector, and add `OTEL_EXPORTER_OTLP_HEADERS` if it needs authentication. This
      is also how the audit trail gets off the machine: the local
      `.evidence/audit/` log is tamper-evident, not tamper-proof.
- [ ] **Replace the sandbox domains** (`git.internal.example.com`,
      `registry.npmjs.org`) with your git host, package registries and anything else
      builds need.
- [ ] **Turn on branch protection and CODEOWNERS** on the hosting platform, for every
      ref in `protected_refs`: required reviews from code owners, no direct pushes, no
      force pushes. Put `.evidence/policy.json`, `.claude/`, `.github/workflows/` and
      `managed-settings.json` under CODEOWNERS. The engine stops the agent; only the
      server stops everyone else.
- [ ] **Pin the model.** Set `model` (and `availableModels`, if you restrict choice)
      in managed settings to the model your tool risk assessment validated. Changing it
      then becomes a change under
      [governance/model-and-config-change-control.md](../governance/model-and-config-change-control.md).
- [ ] **Configure approval identity.** For identity-bound approval, set
      `approval.github_allowed_approvers` in the org policy. Note that `approval.mode`
      isn't enforced by engine 2.0.0 (see [policy-reference.md](policy-reference.md#approval)).
- [ ] **Name owners for the compliance control sets.** Every shipped set says
      `Owner: UNASSIGNED`.
- [ ] **Run the canary** after deploying, and after every Claude Code upgrade.
