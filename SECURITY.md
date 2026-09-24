# Security

## Reporting a vulnerability

Report security issues privately via GitHub's private vulnerability reporting on this
repository, or to the address in the repository's contact information. Please do not
open a public issue for a vulnerability.

Include what you found, how to reproduce it (for a gate bypass, the exact tool call or
command and the policy in effect), and what an attacker could achieve. We aim to
acknowledge within a few working days. A confirmed gate bypass is fixed with a new
labelled regression case in `plugins/evidence-sdlc/scripts/tests/engine-tests.py`, so
the bypass stays closed.

## Threat model for this project

This repository ships **configuration that grants and restricts an agent's behaviour**:
a policy engine behind Claude Code hooks that allows or denies tool calls, a
managed-settings template, and skills that shape what an agent does. The adversary we
design against is **the agent itself** — mistaken, over-eager, or steered by injected
content — trying to change source without an approved plan, weaken tests, touch
change-controlled paths, approve its own work, push to protected branches, release to
production, or leak a secret. The classes of issue that matter most:

- A gate that **fails open** — silently does not fire, or allows on bad input. A policy
  gate that is quietly disabled is worse than no gate, because people trust it.
- A **bypass** — any tool call or command form that achieves a denied outcome.
- A **permission or sandbox template that is more permissive than documented.**
- A **skill whose instructions could be steered** by content it is asked to process.
- Anything that would cause a **credential or secret to be read, logged, or transmitted.**

## How the gates work (v2)

- **One engine.** Every PreToolUse decision for Edit, Write, MultiEdit, NotebookEdit,
  Bash, Agent and Task goes through one Python engine
  (`plugins/evidence-sdlc/scripts/engine/`, standard library only) via
  `bash ${CLAUDE_PLUGIN_ROOT}/scripts/engine/hook.sh`. There are no hook `if` filters;
  every Bash call is parsed (shlex, control operators, wrappers, `bash -c`, `$(…)`,
  `eval`), and Bash writes are judged like Edit/Write. Commands whose file effects
  cannot be determined (inline interpreter code that writes, `patch`, `git apply`,
  archive extraction, `curl -O`) are denied.
- **Fails closed.** Malformed or empty hook input, a missing `python3`, or any engine
  exception on PreToolUse results in a deny (engine cases V2G-01*). `jq` is no longer
  required. Invoking via `bash <script>` means a lost execute bit (e.g. after unzipping)
  does not disable the gate.
- **Liveness canary.** Every session must print "Evidence Chain gates live" at start.
  If it does not, the hooks are not running in that deployment — for example, if plugin
  hooks do not run under `allowManagedHooksOnly` in your Claude Code version (Anthropic
  does not document this). Deploy `docs/managed-hooks.example.json` as managed hooks
  instead, and re-run the canary.
- **Control plane.** Agents cannot write settings, hooks, the policy, the secrets
  allowlist, approval/state records, the audit log, `managed-settings.json` or
  `.mcp.json`, by any tool (cases V2G-09*). So an agent cannot grant itself a
  `CHANGE_TICKET`, `RELEASE_APPROVAL` or `EVIDENCE_ACTIVE_CHANGE`.
- **Secrets.** Written content, Bash command text, heredoc bodies and staged diffs are
  scanned; findings are denied and only a fingerprint is shown, never the value
  (cases V2K-01*).
- **Audit.** Every agent write/Bash call and every deny (with rule and reason) is
  appended to a hash-chained `.evidence/audit/<session>.jsonl`; `evidence audit verify`
  detects altered or removed lines (cases V2A-02*).

The full rule list with its regression cases is in `docs/gates-reference.md`; the
regression suite is `python3 plugins/evidence-sdlc/scripts/tests/engine-tests.py`.

## Known limitations

State these to anyone relying on the gates:

- **The gates govern the agent, not people.** A human working in a terminal outside
  Claude Code is not gated. Server-side branch protection and CODEOWNERS on your
  hosting platform are the authoritative merge control; the plugin cannot configure
  them.
- **Local approval identity is not cryptographic.** In prompt or terminal approval mode
  the approver recorded is the machine's `git user.email` — whoever is at the keyboard.
  GitHub approval mode (`evidence approve <KEY> --github-pr N`) is identity-bound
  through GitHub.
- **The audit log is tamper-evident, not tamper-proof.** Someone with shell access
  outside the agent can rewrite a whole chain consistently. Tamper resistance requires
  shipping records off the machine: set the OTel collector endpoint in managed settings,
  or retain the log as a CI artifact.
- **Command analysis is a parser, not a sandbox.** It covers the forms listed in
  `docs/gates-reference.md`; a write path it does not model is a bypass we want
  reported. Production-release detection uses a policy list of deploy tools; an
  unlisted deploy path is not caught.
- **Secret detection is pattern-based** and will miss some credential formats.
- **Protection depends on the policy.** Change-controlled paths, tier floors and test
  globs come from policy; paths your policy does not name are not treated specially.
- **Owner actions remain:** branch protection and CODEOWNERS, the marketplace value in
  `strictKnownMarketplaces`, the OTel endpoint, sandbox network domains, GitHub approval
  configuration, enabling `.github/workflows/ci.yml`, and running the canary after
  deploying managed settings.

### Platform limits

- **Windows is not supported.** Hooks are launched through `bash`, TTY approval needs
  `/dev/tty`, and the nested-session check uses `ps`. WSL works; native Windows does not.
- **Detection versus prevention.** The pre-check blocks what it can parse. The integrity
  monitor catches what it could not, after the command runs, and restores control-plane
  files. With `EVIDENCE_SIGNING_KEY` deployed and the sandbox on, forged records are
  rejected. Without the key, forgery is detected but not prevented.
- **Very large repositories.** Each Bash call snapshots `git status`. If that exceeds
  the time limit, the call is recorded as unchecked (an integrity violation), not
  silently passed.

## What this project deliberately does not do

- It does not ship credentials, tokens, or endpoints for any third-party service (the
  OTel endpoint in the template is a placeholder).
- It does not include any MCP server implementation. `.mcp.json.example` is a template
  with placeholders; you decide what to connect and under what scope.
- It does not enable any connector by default.

## Using this safely

- **Read the engine and hook configuration before installing.** They run on your
  machine, in your repositories, with your permissions. That is the point, and it is
  also the risk.
- **Run the canary** in every deployment and after every Claude Code upgrade.
- **Run the regression suite** after changing the org or repo policy.
- Treat any third-party MCP server as a supply-chain dependency holding credentials to a
  business system. Scope the credential; prefer read-only.
