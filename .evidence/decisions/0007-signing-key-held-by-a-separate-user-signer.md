# 0007. The signing key is held by a separate-user signer that never runs a program, and signs typed records by channel

Status: Proposed
Date: 2026-09-25
Deciders: Suparn Bector (maintainer); second approver Harshil (Tier 3)
Tracker: PILOT-61   Spec: intent/2026-09-25-signer-key-isolation/spec.md
Supersedes: none (withdraws ADR-0003 §4 for deployments in signer mode)   Relies on: ADR-0003 rev. 2, ADR-0004 rev. 3, ADR-0005 (PILOT-62), ADR-0006 (PILOT-59)
Superseded-by:

Stored at `.evidence/decisions/NNNN-<slug>.md`. Numbers are never reused. An accepted
ADR is never edited except to change its Status or set Superseded-by — a changed
decision is a new ADR.

## Context
- Every signed record is an HMAC-SHA256 with one symmetric key, `EVIDENCE_SIGNING_KEY`. `managed-settings.json` delivers it in `env`, so every hook process holds it (`signing.key()` reads `os.environ`).
- The same hook processes run git and `gh` in a repository the agent shapes. ADR-0003 §4 accepts two residual paths to the key: a check-then-use race in the hook's git, and same-user inspection of a hook's environment. With the key, every local record can be forged, including approvals and clears, and CI results, because CI holds the same key.
- ADR-0004 made the merge decision independent of local records. Local records still decide what the local gates allow, and they are the audit trail.
- Constraints: Python standard library only, macOS and Linux, no new trust in files the agent can write.

## Decision
1. **A signer daemon under its own OS user** (`_evidencesigner` / `evidence-signer`), started by launchd or systemd from a root-owned copy, holds the keyring in a `0400` file. It never starts a program or runs git, and it imports no engine module. An AST test with no allow-list enforces this. It never reads the repository.
2. **Two Unix sockets with peer-credential checks** (`SO_PEERCRED` / `LOCAL_PEERCRED`):
   - `agent.sock` serves the session users' uids, and signs **Class A** records only;
   - `human.sock` serves uid 0 only, and signs **Class H** records. It is reached through `sudo` and a root-owned confirm helper that shows the record on the terminal and needs a typed confirmation.
3. **Typed records.** Each request names a record type. The signer checks it against a schema, sets `rt`, `kid` and `repo`, canonicalises it itself, and returns the signed record. For Class A it keeps its own state, so a caller cannot fork an audit chain, move a stage backwards or into `approved` / `released`, close a violation, pass the `restored` cap, or sign twice for one `tool_use_id`.
4. **Hooks hold no key.** The key leaves `managed-settings.json` `env`. A hook that still receives it denies write tools, because the initial environment cannot be scrubbed.
5. **Fail closed.** In signer mode an unreachable signer means `sign` fails and `verify` is `False`. Hooks deny write tools and Bash. There is no fallback to unsigned mode. The emergency switch is `signer.mode: off` in the root-owned org policy.
6. **Key IDs and separation.** Keys carry IDs and a class (`local`, `ci`). CI signs results with its own key and holds the local keys to verify only. The local signer holds CI keys to verify only, and refuses to sign results. Rotation adds a key and demotes the old one to verify-only. The 2.x key becomes `legacy`, verify-only: records must be migrated by a human, and `verify-range` fails new legacy-signed records or lines when the base is in signer mode.
7. **Prompt approval** becomes a Class A record (`channel: agent`). Local gates accept it up to `prompt_approval_max_tier` (default 2). Tier 3 needs a human-channel or GitHub approval.
8. **One new engine subprocess site,** `signing.py:_sudo_confirm`, is added to the REQ-IMH-22 allow-list.

## Consequences
- **Easier:**
  - no hook, raced program, environment read or modified engine code yields the key;
  - human-only records cannot be forged by anything running as the user;
  - CI results cannot be signed on a developer machine;
  - humans stop handling the key.
- **Harder:**
  - an administrator installs a daemon and a user on every machine;
  - human actions ask for `sudo`;
  - hooks add a few local socket round trips per call;
  - the CI secret becomes a keyring, and rotation has an owner procedure.
- **Constrained:**
  - every signed record type needs a signer schema;
  - Class A records remain forgeable by a program raced into a hook's git, or by any user process when the sandbox is off. They are local detection data, and `verify-range` stays the authority for merges;
  - the human channel depends on `sudo` needing a password per terminal.
- **Cost to reverse:** low. `signer.mode: off` restores 2.x behaviour. Records signed under local kids stay verifiable if the keyring is exported back to an environment key.
- **Review trigger:** reopen if the standard library gains Ed25519, if Claude Code runs hooks in a sandbox, if Class A forgery is observed in practice, or if `sudo` cannot be relied on as the human-presence factor.

## Alternatives
| Option | Why it lost |
| --- | --- |
| Keep the key in hooks and harden git further (ADR-0003) | Each fix leaves another path; environment inspection is not a git problem |
| A same-user signer (LaunchAgent, or a keychain item) | Any user process, including a raced one, can read the item or inspect the signer |
| A one-shot helper per request, with the key on a file descriptor | The key must come from a file the user can open; no durable state for chain and stage checks |
| A `NOPASSWD` sudo rule for signing | The agent's shell could use it too |
| Ed25519 through `openssl` subprocesses | A subprocess on the key path; LibreSSL and OpenSSL differ |
| Hardware keys (Secure Enclave, TPM) | Platform-specific, and no standard-library access |
| The signer checks GitHub approvals itself | A token and network on the key path; `verify-range` already does it on the server |
