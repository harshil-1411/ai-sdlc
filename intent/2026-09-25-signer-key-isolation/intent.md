# Intent: Isolate the signing key in a signer that never runs git

Tracker: PILOT-61   Author: Suparn Bector (maintainer), drafted by Claude from ADR-0003 §4 and the PILOT-58 reviews   Date: 2026-09-25   Status: draft

## Problem
Every signed local record (approvals, change state, violations, audit entries, integrity snapshots) is an HMAC made with one symmetric key, `EVIDENCE_SIGNING_KEY` (`engine/signing.py`). Today:

- **The key sits in the environment of every hook process.** `managed-settings.json` delivers it in `env`, Claude Code passes it to hooks, and `signing.key()` reads `os.environ`. The sandbox `credentials.envVars` deny keeps it out of the agent's Bash, and nothing else does.
- **The same processes run git and `gh` in a repository the agent shapes** (`state.run_git`, `run_gh`, `integrity.snapshot` / `check`). ADR-0003 hardened those calls (`GIT_NEUTRAL`, `check_git_config`, `_child_env` removes the key from children), but its §4 states two residual paths that local hardening cannot close:
  - **a race:** a command the agent started changes config or attributes between `check_git_config` and the git call, so git runs a program in the hook's context (unsandboxed, the user's uid);
  - **environment inspection:** any same-user process can read a running hook's initial environment where the OS allows it (`/proc/<pid>/environ` on Linux, `ps eww` / `KERN_PROCARGS2` on macOS). `unsetenv` does not clear the initial block.
- **With the key, an agent can forge every local record,** including the human-only ones: `approval.json`, `clear-violations`, `set-tier`, `release`, `override`. The key is shared with CI (`docs/managed-settings.md` step 4), so it can also sign test-result sidecars (`evidence results sign`).
- **Human terminal actions teach people to handle the key.** `_require_key_if_signed` tells the human to paste a `python3 -c` one-liner that reads the key from `managed-settings.json` into their shell (`lifecycle.py:58–80`, `docs/managed-settings.md:207`).

ADR-0004 moved the merge decision to a server-side gate that does not trust local records alone, so key exposure no longer decides what merges. It still decides whether the local layer can be trusted at all, and ADR-0003's review trigger, and ADR-0004's, are "when PILOT-61 isolates the key".

## Proposed outcome
1. **No process that runs git holds the key,** in its environment or its memory. The key lives only in a signer that runs as a separate OS user, never starts a program, and is reachable only over Unix sockets with peer-credential checks.
2. **The signer signs typed records only,** after validating them. A compromised hook, or a program raced into the hook's git, can at most obtain signatures the agent's own lifecycle could already produce (Class A). It cannot obtain a human-only record (Class H) or a CI result (Class C).
3. **Human actions reach the signer through a human-presence channel** (`sudo` plus a terminal confirmation in a root-owned helper), and nobody handles the key any more.
4. **CI keeps its own key** (a distinct key ID), so a local compromise cannot sign results, and CI can still verify local records.
5. **Keys rotate** with key IDs, and 2.x records keep verifying as history.
6. **The signer being down fails closed.** It never falls back to unsigned mode.

**Measure:**
- with `signer.mode: required`, no hook process's environment contains a key (test: a hook writes `os.environ` to a file; manual: `ps eww` on a live hook);
- every Class H request over the agent socket is refused, each with a test;
- ADR-0003 §4 is withdrawn for deployments in signer mode, and the remaining residual (Class A forgery through the race) is stated;
- the REQ-IMH-22 subprocess allow-list grows by exactly one named site.

## Affected users and systems
- The gate engine (`signing.py` and every caller), the lifecycle CLI's human actions, `verify-range`, `evidence results sign`.
- A new component: the signer daemon, its installer, and launchd / systemd units. Installing it is an administrator action (`sudo`).
- Platform teams who deploy `managed-settings.json`: the key leaves `env`.
- Maintainers and approvers: terminal actions ask for `sudo` and a confirmation instead of the key.
- CI: the `EVIDENCE_SIGNING_KEY` secret's value becomes a keyring.

## Regulated record impact
Yes. Every signed record gains `kid` and `rt` fields, and the signer decides which records it will sign. Human-only records gain `channel: human`. 2.x records stay valid as history. Nothing for end customers.

## Compliance evidence impact
Yes. `SECURITY.md`, `governance/control-mapping.md` and `governance/supplier-audit-packet.md` state that the hooks hold the key and describe the residual risk. Those claims are restated. No regulatory framework is established for this repository (`.evidence/context/compliance.md`: all `[ASK]`).

## Data classification
Secret: the signing keys. No step of this change may read, print or log the key on this machine, or anything under `/Library/Application Support/ClaudeCode/`. Tests use generated test keys in scratch directories only.

## Constraints
- **Python standard library only,** on macOS and Linux, as the engine is today. No `cryptography` package and no `openssl` subprocess.
- **The signer never runs git or any other program.** An AST test enforces it, with no allow-list.
- **No weakening of what merges.** `verify-range` rules 0–5 are only tightened (key IDs on new records).
- **Fail closed.** No silent fallback to unsigned mode when the signer is required.
- **Backwards compatible:** `signer.mode: off` (the default) keeps 2.x behaviour exactly, and 2.x records, logs and results still verify.
- **Tier 3 process:** plan approval by a second human (Harshil); review agents one at a time; no edits during a review.
- **Merge order** PILOT-62 → PILOT-60 → PILOT-59 → PILOT-61 (see the plan, "Coordination").

## Out of scope
- Asymmetric signatures (Ed25519): no standard-library implementation. Recorded in ADR-0007 as the next step if a dependency becomes acceptable.
- Hardware-backed keys (Secure Enclave, TPM, HSM).
- Sandboxing the hook's own git calls, which would close the race itself.
- Windows (unsupported today, `SECURITY.md` "Platform limits").

## Open questions
- Does the owner accept a root-installed daemon and a dedicated OS user on every developer machine? Owner: maintainer, at approval.
- Is `sudo` on the target machines password-protected per terminal (no `NOPASSWD`, no `timestamp_type=global`)? The human channel relies on it. Owner: platform team.
- Should prompt-channel approval (`/evidence-sdlc:approve`) stay for Tier 1–2 in signer mode (spec REQ-KEY-07)? Owner: maintainer.
