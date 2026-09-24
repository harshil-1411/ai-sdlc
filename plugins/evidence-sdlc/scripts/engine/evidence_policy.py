"""Evidence Chain gate engine: every PreToolUse decision in one place.

decide_pre(ctx) returns a Decision. The hook shell (hook.py) handles I/O and fails
closed on any error. Rules are driven by the merged policy (state.load_policy)
and the active change's state (.evidence/changes/<KEY>/).
"""
import fnmatch
import os
import re
import subprocess

import cmdparse
import secretscan
import state as st


class Decision:
    __slots__ = ("allow", "reason", "rule", "context")

    def __init__(self, allow=True, reason="", rule="", context=""):
        self.allow = allow
        self.reason = reason
        self.rule = rule
        self.context = context


ALLOW = Decision()


def deny(rule, reason):
    return Decision(False, reason, rule)


class Ctx:
    def __init__(self, payload, cwd=None, env=None):
        self.payload = payload or {}
        self.env = env if env is not None else os.environ
        self.cwd = os.path.realpath(self.payload.get("cwd") or cwd or os.getcwd())
        self.root = st.repo_root(self.cwd)
        self.policy = st.load_policy(self.root)
        self.branch = st.current_branch(self.root)
        self.session = self.payload.get("session_id") or ""
        self.permission_mode = self.payload.get("permission_mode")
        self.agent_type = (self.payload.get("agent_type") or "").split(":")[-1]
        self.tool = self.payload.get("tool_name") or ""
        self.tool_input = self.payload.get("tool_input") or {}
        self._key = None
        self._state = None
        self._loaded = False

    def change(self):
        if not self._loaded:
            self._key, self._key_src = st.active_key(self.root, self.policy, self.branch)
            self._state = st.load_state(self.root, self._key) if self._key else None
            self._loaded = True
        return self._key, self._state


# ------------------------------------------------------------------ write rules

def _user_control_plane(real, policy):
    home = os.path.expanduser("~")
    for pat in policy.get("user_control_plane", []):
        p = os.path.expanduser(pat)
        if fnmatch.fnmatch(real, p) or fnmatch.fnmatch(real, p.replace("/**", "")):
            return pat
        if p.endswith("/**") and (real + "/").startswith(p[:-2]):
            return pat
    return None


_APPROVAL_LINE = re.compile(
    # "Approved by: <someone>" / "Approver: <someone>" / "| Approved by | <someone> |" / "Status: approved",
    # at the start of a line. Placeholders (<…>, [ASK], PENDING, TBD, n/a) and prose mid-sentence don't match.
    r"(?:^[ \t>*_|-]*|[ \t]{2,}|\|[ \t]*)(?:\*\*)?(?:approved[ -]by|approver)(?:\*\*)?[ \t]*[:|][ \t]*(?:\*\*)?[ \t]*"
    r"(?!<|\[|pending|tbd|—|n/a|none\b|\||$)\S"
    r"|^[ \t>*_-]*(?:\*\*)?status(?:\*\*)?[ \t]*:[ \t]*(?:\*\*)?[ \t]*approved\b",
    re.I | re.M)


def check_write(ctx, raw_path, content=None, kind="write", detail=""):
    pol = ctx.policy
    rel, real = st.normalize(raw_path, ctx.cwd, ctx.root)
    if real and _user_control_plane(real, pol):
        return deny("control-plane",
                    f"{raw_path} is Claude Code or Evidence Chain configuration outside the repository. "
                    "An agent session may not change the configuration that governs it. A human edits this file directly.")
    if rel is None:
        return ALLOW  # outside the repository: not this framework's concern
    if st.glob_match(rel, pol.get("control_plane", [])):
        return deny("control-plane",
                    f"{rel} is part of the control plane (settings, policy, approvals, change state or audit log). "
                    "An agent may not write it. A human edits it directly, or runs the `evidence` command that owns it "
                    "(for example `evidence approve <KEY>` in their own terminal).")
    if ctx.agent_type and ctx.agent_type in pol.get("read_only_agents", []):
        return deny("read-only-agent",
                    f"The {ctx.agent_type} agent is read-only by policy and may not write {rel}. "
                    "Return the proposed change to the main session instead.")
    if content and pol.get("scan_secrets", True):
        d = _secret_decision(ctx, content, f"{rel}")
        if d is not None:
            return d
    if content and _APPROVAL_LINE.search(content) and re.search(r"(^|/)(plan|spec|intent)(\.md|/[^/]+\.md)$", rel):
        return deny("self-approval",
                    f"{rel}: approval is not written into planning artifacts. It is recorded only in "
                    ".evidence/changes/<KEY>/approval.json by a human (`/evidence-sdlc:approve <KEY> <plan-sha>`), and it "
                    "binds to the plan's hash. Remove the approval line; if the human already said they approve, ask "
                    "them to send that command.")
    if ctx.env.get("FIX_TASK") == "1" and st.is_test_path(rel, pol) and st.file_in_commit(ctx.root, "HEAD", rel):
        # Legacy switch (pre-v2): a human started the session as a fix task.
        return deny("test-weakening",
                    f"This is a fix task (FIX_TASK=1) and {rel} is an existing test. Fix the code, not the test. "
                    "If the test itself is wrong, stop and say so; a human decides.")
    if st.glob_match(rel, pol.get("ungated", [])) and not st.glob_match(rel, pol.get("always_gated", [])):
        return ALLOW
    return check_gated(ctx, rel, kind, detail)


def _allowlist(ctx):
    p = os.path.join(ctx.root, ".evidence", "secrets-allowlist.json")
    try:
        import json
        with open(p) as f:
            data = json.load(f)
        return [e["fingerprint"] if isinstance(e, dict) else e for e in data.get("fingerprints", data if isinstance(data, list) else [])]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []


def _secret_decision(ctx, text, where):
    findings = secretscan.scan(text, _allowlist(ctx))
    if not findings:
        return None
    desc = "; ".join(f"{f['rule']} on line {f['line']} (fingerprint {f['fingerprint']})" for f in findings[:5])
    return deny("secret",
                f"Possible secret in {where}: {desc}. Secrets must never be written to the repository or passed on a "
                "command line. Load them from the environment or a secret manager. If this is a false positive, a human "
                "adds the fingerprint to .evidence/secrets-allowlist.json.")


def check_gated(ctx, rel, kind="write", detail=""):
    """A write to source: needs an approved, active change that claims the path."""
    pol = ctx.policy
    key, state = ctx.change()
    what = f"{'Deleting' if kind == 'delete' else 'Writing'} {rel}" if rel else f"This command ({detail})"
    if not key:
        return deny("no-active-change",
                    f"{what} needs an active change, and none was found ({ctx._key_src} carries no tracker key). "
                    "Create or switch to a branch named with the key (e.g. feature/ABC-123-short-name), then run "
                    "`evidence change start ABC-123 --tier <1|2|3> --kind feature|fix|chore`.")
    if not state:
        return deny("no-change-state",
                    f"{what} needs change {key} to be started. Run `evidence change start {key} --tier <1|2|3> "
                    "--kind feature|fix|chore`, write the artifacts its tier requires, and ask a human to approve the plan.")
    import signing
    if signing.verify(state) is False:
        return deny("state-unsigned",
                    f"{what}: the lifecycle state for {key} is not signed by the gate engine, so it may have been "
                    "altered. A human re-records it (`evidence change set-tier`, or start the change again).")
    tier = int(state.get("tier") or 1)
    missing = [a for a in st.required_artifacts(tier) if not st.find_artifact(ctx.root, key, a, state)]
    if missing:
        return deny("missing-artifacts",
                    f"{what}: change {key} is Tier {tier}, which requires {', '.join(st.required_artifacts(tier))} before "
                    f"source changes. Missing: {', '.join(m + '.md' for m in missing)}. "
                    f"`evidence change status {key}` lists what is needed.")
    plan = st.find_artifact(ctx.root, key, "plan", state)
    problems = st.plan_problems(plan)
    if problems:
        return deny("plan-stub", f"{what}: the plan for {key} ({os.path.relpath(plan, ctx.root)}) is not a real plan yet: "
                                 + "; ".join(problems) + ".")
    tier_lines = re.findall(r"^Risk tier:\s*(\S+)", open(plan, encoding="utf-8", errors="replace").read(), re.M)
    if len(tier_lines) != 1 or not re.fullmatch(r"[123]", tier_lines[0].rstrip("—-,;:")):
        return deny("tier-mismatch",
                    f"{what}: the plan must state its tier exactly once as `Risk tier: <1|2|3>` "
                    f"(found {len(tier_lines)} line(s): {', '.join(tier_lines) or 'none'}).")
    m_tier = re.match(r"[123]", tier_lines[0])
    if m_tier and int(m_tier.group(0)) != tier:
        return deny("tier-mismatch",
                    f"{what}: the plan says Risk tier {m_tier.group(0)} but change {key} is recorded as Tier {tier}. "
                    f"A human reconciles them (`evidence change set-tier {key} <n>`, or fix the plan and re-approve).")
    if state.get("stage") == "released":
        return deny("change-released",
                    f"{what}: change {key} is released. Start a new change for further work.")
    approval = st.load_approval(ctx.root, key)
    prob = st.approval_problem(ctx.root, key, approval, plan)
    if prob and prob not in ("not-approved", "approval-stale") and approval and approval.get("method") == "github":
        try:
            import lifecycle
            if lifecycle.reverify_github(ctx.root, key, plan, approval):
                approval = st.load_approval(ctx.root, key)
                prob = st.approval_problem(ctx.root, key, approval, plan)
        except Exception:
            pass
    if prob and prob not in ("not-approved", "approval-stale"):
        return deny("approval-invalid",
                    f"{what}: the approval record for {key} is not valid ({prob}). It was not written by a human "
                    "approval channel. A human re-approves with `/evidence-sdlc:approve "
                    f"{key} {st.sha256_file(plan)[:12]}`.")
    if not approval:
        sha = st.sha256_file(plan)[:12]
        return deny("not-approved",
                    f"{what}: the plan for {key} has not been approved. Ask a human to review "
                    f"{os.path.relpath(plan, ctx.root)} and send `/evidence-sdlc:approve {key} {sha}` (or run "
                    f"`evidence approve {key} {sha}` in their own terminal). An agent cannot approve its own plan.")
    if approval.get("plan_sha256") != st.sha256_file(plan):
        return deny("approval-stale",
                    f"{what}: the plan for {key} changed after it was approved, so the approval no longer applies. "
                    f"A human must re-read it and send `/evidence-sdlc:approve {key} {st.sha256_file(plan)[:12]}`.")
    if rel:
        floors = pol.get("tier_floors", {})
        floor = max([int(t) for g, t in floors.items() if st.glob_match(rel, [g], icase=True)] or [0])
        if floor > tier:
            return deny("tier-floor",
                        f"{what}: policy sets a minimum of Tier {floor} for this path, but change {key} is Tier {tier}. "
                        f"A human raises the tier with `evidence change set-tier {key} {floor}`; the tier's extra "
                        "artifacts and reviews then apply.")
    if tier >= 3 and pol.get("deny_tier3_auto_modes", True) and ctx.permission_mode in pol.get("tier3_denied_permission_modes", []):
        return deny("tier3-auto-mode",
                    f"{what}: change {key} is Tier 3, which requires per-change human review, but this session is in "
                    f"'{ctx.permission_mode}' mode. Switch to the default permission mode for Tier 3 work.")
    if rel and pol.get("enforce_claims", True):
        claims = st.plan_claims(open(plan, encoding="utf-8", errors="replace").read())
        if not st.claim_matches(rel, claims):
            return deny("outside-claims",
                        f"{what}: {rel} is not in the approved plan's \"Files claimed\" for {key}. Add it to the plan "
                        "(which voids the approval) and ask for re-approval, or leave the file alone.")
    if rel and st.glob_match(rel, pol.get("change_controlled", []), icase=True):
        ticket = ctx.env.get("CHANGE_TICKET", "")
        if not ticket or not re.fullmatch(pol.get("change_ticket_pattern", ".+"), ticket):
            return deny("change-controlled",
                        f"{what}: {rel} is under formal change control (migrations, CI, infrastructure, audit, signing, "
                        "crypto or validation assets). A human starts the session with CHANGE_TICKET set to an approved "
                        f"change record matching {pol.get('change_ticket_pattern')}"
                        + (f" (the current value '{ticket}' does not match)." if ticket else "."))
    if rel and state.get("kind") == "fix" and state.get("fix_base") and st.is_test_path(rel, pol):
        if st.file_in_commit(ctx.root, state["fix_base"], rel):
            return deny("test-weakening",
                        f"{what}: change {key} is a fix past its failing-test stage, and {rel} is a test that existed "
                        "before the fix. Fix the code, not the test. If the test itself is wrong, stop and say so; a human "
                        "decides. New test files are allowed.")
    return ALLOW


# ------------------------------------------------------------------ bash rules

def _read_file(ctx, path):
    try:
        p = path if os.path.isabs(path) else os.path.join(ctx.cwd, path)
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _protected(ref, pol):
    if ref == "*":
        return True
    return any(fnmatch.fnmatchcase(ref, g) for g in pol.get("protected_refs", []))


def _review_gate(ctx, action):
    pol = ctx.policy
    key0, _ = ctx.change()
    open_v = st.open_violations(ctx.root, key0, ctx.branch)
    if open_v:
        return deny("integrity-violation",
                    f"{action} is blocked: the integrity monitor recorded {len(open_v)} unapproved change(s) made by "
                    f"commands the gates could not inspect ({', '.join(sorted({v['path'] for v in open_v})[:5])}). Revert "
                    "them, then a human reviews and runs `evidence change clear-violations "
                    f"{key0 or '<KEY>'}` in their own terminal.")
    if not pol.get("require_review_agents", True):
        return None
    key, state = ctx.change()
    if not key or not state:
        return None
    tier = str(int(state.get("tier") or 1))
    required = pol.get("required_agents", {}).get(tier, [])
    done = st.recorded_agents(ctx.root, key)
    missing = [a for a in required if a not in done]
    if missing:
        return deny("review-agents",
                    f"{action} for change {key} (Tier {tier}) needs these review agents to have run on it first: "
                    f"{', '.join(missing)}. Dispatch them, act on their findings, then retry. "
                    "Runs are recorded automatically in the audit log.")
    return None


def _check_git(ctx, s, bodies=()):
    pol = ctx.policy
    gopts, sub, sargs = cmdparse.git_split(s.argv)
    for opt, val in gopts:
        if opt == "-c" and val:
            k = val.split("=", 1)[0]
            if any(fnmatch.fnmatch(k.lower(), g.lower()) for g in pol.get("deny_git_config_keys", [])):
                return deny("git-config",
                            f"`git -c {k}=…` can run arbitrary programs or change how git authenticates, which bypasses "
                            "command review. Run the plain git command instead.")
        if opt == "--config-env":
            return deny("git-config", "`git --config-env` is not allowed in agent sessions.")
    if sub == "remote" and sargs[:1] and sargs[0] in ("add", "set-url", "rename", "remove", "rm", "set-head", "set-branches"):
        return deny("remote-change",
                    "Changing git remotes is a human action: approvals and reviews are read from the remote, so an agent "
                    "that could repoint it could choose where its approval comes from.")
    if sub == "config":
        setting, skip = [], False
        for a in sargs:
            if skip:
                skip = False
                continue
            if a in ("--file", "-f", "--blob", "--type", "--default", "--comment"):
                skip = True
                continue
            if not a.startswith("-"):
                setting.append(a)
        readonly = any(a in sargs for a in ("--get", "--get-all", "--list", "-l", "--get-regexp", "--show-origin"))
        if setting and not readonly and len(setting) >= 2:
            k = setting[0]
            if any(fnmatch.fnmatch(k.lower(), g.lower()) for g in pol.get("deny_git_config_keys", [])):
                return deny("git-config", f"Setting git config '{k}' can run arbitrary programs; a human sets it.")
    if sub == "push":
        targets, flags = cmdparse.git_push_targets(sargs, ctx.branch)
        bad = [t for t in targets if _protected(t, pol)]
        if bad:
            what = "all branches" if "*" in bad else ", ".join(bad)
            return deny("protected-push",
                        f"This push would update {what}, which is protected. An agent has no route to a protected branch: "
                        "push a feature branch and open a pull request; a human code owner approves and merges.")
        return _review_gate(ctx, "Pushing")
    if sub == "commit":
        return _check_commit(ctx, sargs, bodies)
    return None


def _check_commit(ctx, sargs, bodies=()):
    pol = ctx.policy
    heredoc = "\n".join(bodies)
    msgs, flags = cmdparse.git_commit_messages(sargs, lambda p: heredoc if p == "-" else _read_file(ctx, p))
    # `git commit -m "$(cat <<'EOF' ... EOF)"`: the message text lives in the heredoc.
    msgs = [heredoc if ("$(" in m or "HEREDOC" in m) and heredoc else m for m in msgs]
    if not msgs:
        if "amend" in flags and "no-edit" in flags:
            head = st.git(["log", "-1", "--format=%B"], ctx.root) or ""
            msgs = [head]
        elif "reuse" in flags:
            msgs = [""]
        else:
            return deny("commit-message",
                        "Give the commit message on the command line (-m or -F); an agent session cannot use an editor.")
    msg = "\n".join(msgs)
    keys = st.find_keys(msg, pol)
    if not keys:
        return deny("commit-key",
                    "The commit message carries no tracker key (pattern "
                    f"{pol['key_pattern']}; tokens like UTF-8 or SHA-256 do not count). Every commit must carry the key "
                    "so the chain from requirement to test to evidence holds. The key in the branch name alone is not enough.")
    key, _ = ctx.change()
    if key and key not in keys:
        return deny("commit-key",
                    f"The active change is {key}, but the commit message names {', '.join(keys)}. Commit under the active "
                    "change's key, or switch branches.")
    if pol.get("require_agent_trailer", True) and ctx.session:
        m = re.search(r"^Agent-Session:\s*(\S+)\s*$", msg, re.M)
        if not m or m.group(1) != ctx.session:
            return deny("agent-trailer",
                        "Commits made by an agent must say which session made them. End the commit message with the "
                        f"trailer line:\nAgent-Session: {ctx.session}")
    if key and pol.get("commit_requires_audit", True):
        staged = set((st.git(["diff", "--cached", "--name-only"], ctx.root) or "").split())
        tracked = set((st.git(["ls-files", ".evidence"], ctx.root) or "").split())
        need = []
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", ctx.session or "")[:80]
        unstaged = set((st.git(["diff", "--name-only"], ctx.root) or "").split())
        for rel in (f".evidence/audit/{safe}.jsonl", f".evidence/changes/{key}/state.json",
                    f".evidence/changes/{key}/approval.json", f".evidence/audit/approval-{key}.jsonl"):
            if not os.path.isfile(os.path.join(ctx.root, rel)):
                continue
            if (rel not in staged and rel not in tracked) or rel in unstaged:
                need.append(rel)
        if need:
            return deny("commit-evidence",
                        "The change's evidence must be committed with it, up to date. Stage it first: git add " + " ".join(need))
        _, cstate = ctx.change()
        plan = st.find_artifact(ctx.root, key, "plan", cstate) if cstate else None
        if plan and pol.get("enforce_claims", True):
            claims = st.plan_claims(open(plan, encoding="utf-8", errors="replace").read())
            outside = [p for p in staged if not p.startswith(".evidence/") and not st.glob_match(p, pol.get("ungated", []))
                       and not st.claim_matches(p, claims)]
            if outside:
                return deny("outside-claims",
                            f"The commit includes files outside the approved plan's claims for {key}: "
                            f"{', '.join(sorted(outside)[:6])}. Unstage them, or amend the plan and get it re-approved.")
    if pol.get("scan_secrets", True):
        diff = st.git(["diff", "--cached", "-U0", "--no-color"], ctx.root, timeout=20) or ""
        if "all" in flags:
            diff += st.git(["diff", "-U0", "--no-color"], ctx.root, timeout=20) or ""
        added = "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
        d = _secret_decision(ctx, added, "the staged changes")
        if d is not None:
            return d
        d = _secret_decision(ctx, msg, "the commit message")
        if d is not None:
            return d
    return None


def _check_gh(ctx, s):
    pol = ctx.policy
    args = s.argv[1:]
    words = [a for a in args if not a.startswith("-")]
    if words[:2] == ["pr", "merge"]:
        if pol.get("deny_agent_merge", True) or "--admin" in args:
            return deny("agent-merge",
                        "Merging is a human decision in this repository: a code owner reviews and merges the pull request. "
                        "`gh pr merge` is not available to an agent session.")
    if words[:1] == ["api"]:
        method = None
        for i, a in enumerate(args):
            if a in ("-X", "--method") and i + 1 < len(args):
                method = args[i + 1].upper()
            elif a.startswith("--method="):
                method = a.split("=", 1)[1].upper()
        endpoint = next((w for w in words[1:] if "/" in w), "")
        if method in ("PUT", "POST", "PATCH", "DELETE") and re.search(r"/merge\b|/protection\b|/rulesets\b|/branches/[^/]+/rename|/git/refs", endpoint):
            return deny("agent-merge",
                        f"`gh api -X {method} {endpoint}` changes merges, branch protection or refs. That is a human action.")
        if method is None and re.search(r"/merge\b", endpoint) and any(a in ("-f", "-F", "--field", "--raw-field", "--input") for a in args):
            return deny("agent-merge", "`gh api` with fields against a /merge endpoint is a merge; that is a human action.")
    if words[:2] == ["repo", "set-default"]:
        return deny("remote-change", "Changing the default GitHub repository is a human action (approvals are read from it).")
    if words[:2] == ["pr", "review"] and any(a in ("--approve", "-a") for a in args):
        return deny("self-approval", "Approving a pull request is a human reviewer's action, not the agent's.")
    if words[:2] in (["pr", "comment"], ["issue", "comment"]) and "/approve-plan" in " ".join(args):
        return deny("self-approval", "A `/approve-plan` comment is a human's approval; the agent may not post one.")
    if words[:1] == ["api"]:
        joined = " ".join(args)
        if re.search(r"/reviews\b", joined) and re.search(r"APPROVE", joined):
            return deny("self-approval", "Submitting an approving review through the API is a human action.")
        if "graphql" in words and re.search(r"mergePullRequest|enablePullRequestAutoMerge|addPullRequestReview|"
                                            r"BranchProtectionRule|updateRef|deleteRef", joined):
            return deny("agent-merge", "This GraphQL mutation merges, approves or changes protection; that is a human action.")
        if "/approve-plan" in joined:
            return deny("self-approval", "A `/approve-plan` comment is a human's approval; the agent may not post one.")
    if words[:2] == ["pr", "create"]:
        return _review_gate(ctx, "Opening a pull request")
    return None


def _check_http(ctx, s):
    """curl/wget/http straight at a code host's API with a mutating method."""
    if s.prog not in ("curl", "wget", "http", "https", "xh"):
        return None
    joined = " ".join(s.argv[1:])
    if not re.search(r"api\.github\.com|/api/v[34]/|gitlab\.[^/\s]+/api", joined):
        return None
    mutating = re.search(r"(-X|--request)\s*(POST|PUT|PATCH|DELETE)|\b(POST|PUT|PATCH|DELETE)\b|--data|-d\s|--json", joined)
    if mutating:
        return deny("agent-merge", "Mutating a code host's API directly (reviews, merges, protection, refs) is not "
                                   "available to an agent session; use the gh commands the gates understand, or ask the human.")
    return None


def _check_deploy(ctx, s):
    pol = ctx.policy
    what = cmdparse.deploy_invocation(s)
    if not what:
        return None
    prod, why = cmdparse.targets_production(s, pol.get("prod_words", []))
    if not prod:
        return None
    if "computed at run time" in why and not pol.get("treat_unknown_deploy_target_as_production", True):
        return None
    approval = ctx.env.get("RELEASE_APPROVAL", "")
    pat = pol.get("release_approval_pattern", ".+")
    if not approval or not re.search(pat, approval):
        return deny("release-approval",
                    f"`{what}` {why}. Production changes need a release authorization: a human starts the session with "
                    f"RELEASE_APPROVAL set to the approved release record (matching {pat}). The agent cannot supply it."
                    + (f" The current value '{approval}' does not match." if approval else ""))
    verify = pol.get("release_approval_verify_command")
    if verify:
        try:
            r = subprocess.run(verify.replace("{approval}", approval), shell=True, cwd=ctx.root,
                               capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                return deny("release-approval",
                            f"Release approval '{approval}' could not be verified by the policy's check "
                            f"({r.stderr.strip()[:200] or 'non-zero exit'}).")
        except (OSError, subprocess.TimeoutExpired) as e:
            return deny("release-approval", f"Release approval verification failed to run: {e}.")
    return None


_NETWORK_PROGS = {"curl", "wget", "nc", "ncat", "netcat", "socat", "ssh", "scp", "sftp", "telnet", "ftp", "http",
                  "https", "xh", "aria2c", "rsync"}
_CLAUDE_BINS = {"claude", "claude-code"}
_TTY_WRAPPERS = {"script", "unbuffer", "expect", "socat", "tmux", "screen", "pty", "empty", "ptyrun"}


def _launches_claude(s):
    if not s.argv:
        return False
    if s.prog in _CLAUDE_BINS:
        return True
    joined = " ".join(s.argv[1:])
    if s.prog in ("npx", "bunx", "pnpx", "yarn", "pnpm", "npm") and "@anthropic-ai/claude-code" in joined:
        return True
    if s.prog in _TTY_WRAPPERS and re.search(r"(^|[\s/'\"])claude(-code)?(\s|$|['\"])", joined):
        return True
    if s.prog in cmdparse.INTERPRETERS and re.search(r"(^|[\s/'\"])claude(-code)?(\s|['\"]|$)", joined) and "-c" in s.argv:
        return True
    return False


def _is_evidence_cli(s):
    if not s.argv:
        return False
    if s.prog == "evidence":
        return True
    if s.prog.startswith("python") and len(s.argv) > 1 and os.path.basename(s.argv[1]) == "evidence":
        return True
    return False


def _expand(target, cwd):
    """Brace and glob expansion the shell would do, so wildcards can't hide protected files."""
    import glob as _glob
    outs = [target]
    m = re.search(r"\{([^{}]*,[^{}]*)\}", target)
    if m:
        outs = [target[:m.start()] + alt + target[m.end():] for alt in m.group(1).split(",")]
    res = []
    for t in outs:
        if any(ch in t for ch in "*?["):
            base = t if os.path.isabs(t) else os.path.join(cwd, t)
            hits = _glob.glob(os.path.expanduser(base))
            res.extend(hits or [t])
        else:
            res.append(t)
    return res


def _dir_problem(ctx, rel):
    """A write or delete aimed at a whole directory."""
    if rel == "":
        return deny("bulk-write", "This command targets the whole repository. Name the files instead.")
    for pat in ctx.policy.get("control_plane", []):
        prefix = re.split(r"[*?\[]", pat, 1)[0].rstrip("/")
        if prefix == rel or prefix.startswith(rel + "/"):
            return deny("control-plane", f"{rel}/ contains control-plane files ({pat}); an agent may not remove or "
                                         "overwrite it.")
    return None


_TMP_DIRS = ("/tmp/", "/private/tmp/", "/var/tmp/", "/var/folders/")


def _check_script(ctx, script, cwd):
    pol = ctx.policy
    if not pol.get("deny_opaque_writes", True) or not script:
        return None
    if "$" in script or "`" in script:
        return deny("opaque-write", f"Running a script whose path is computed at run time ({script}) cannot be checked.")
    rel, real = st.normalize(script, cwd, ctx.root)
    plugin_root = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    if real and real.startswith(plugin_root + os.sep):
        return None
    if rel is None:
        tmp = tuple(os.path.realpath(d) + "/" for d in _TMP_DIRS if os.path.isdir(d))
        if real and (real.startswith(_TMP_DIRS) or real.startswith(tmp) or real.startswith(os.path.realpath(os.environ.get("TMPDIR", "/tmp")) + "/")):
            return deny("opaque-write",
                        f"Running {script} from a temporary directory executes code the gates never saw written. Put the "
                        "script in the repository under the approved plan's claims, or ask the human to run it.")
        return None
    if st.glob_match(rel, pol.get("ungated", [])):
        return deny("opaque-write",
                    f"{rel} is an ungated file type (documentation), so running it as a program would execute code the "
                    "gates never checked. Scripts must be source files written under an approved plan.")
    return None


_BG = re.compile(r"(?<![&>|<0-9])&(?![&>])")


def _background(command):
    """True if the command puts work in the background (`cmd &`, `(cmd &)`). Heredoc
    bodies and quoted text are removed first, and `&&`, `>&`, `&>` are not backgrounding."""
    stripped, _ = cmdparse._strip_heredocs(command)
    stripped = re.sub(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"", "''", stripped)
    return bool(_BG.search(stripped))


def check_bash(ctx, command):
    pol = ctx.policy
    if re.search(r"EVIDENCE_SIGNING_KEY|/proc/[^\s]*/environ|\bps\b[^|;&]*\be(ww|w|e)\b|\bprintenv\b|^\s*env\s*$|os\.environ\b|process\.env\b|ENV\[|managed-settings\.json|ClaudeCode/", command):
        return deny("secret-access",
                    "This command could read the Evidence Chain signing key or the managed settings. Environment dumps "
                    "and those files are not available to an agent session.")
    if pol.get("deny_background", True) and _background(command):
        return deny("background",
                    "Running work in the background (`&`) is not available to an agent session: what it does after "
                    "this command returns happens where the gates and the integrity monitor cannot see it. Run it in "
                    "the foreground, or ask the human to start long-running processes.")
    simples, ok, bodies = cmdparse.split_simple(command)
    if not ok:
        return deny("unparseable",
                    "This command could not be parsed reliably (unbalanced quotes or nesting too deep), so the gates "
                    "cannot tell what it does. Rewrite it more simply, or split it into separate commands.")
    if pol.get("scan_secrets", True):
        d = _secret_decision(ctx, command, "this command")
        if d is not None:
            return d
    cwd = ctx.cwd
    for s in simples:
        if pol.get("deny_persistence", True) and (set(s.wrappers) - {s.prog}) & cmdparse.PERSISTENCE or (
                s.prog in cmdparse.PERSISTENCE and not (s.prog == "crontab" and "-l" in s.argv)):
            return deny("persistence",
                        "Starting work that outlives this command (nohup, setsid, at, crontab, launchctl, systemd-run) "
                        "is not available to an agent session: its effects would happen after the gates look.")
        if ctx.agent_type and ctx.agent_type in pol.get("read_only_agents", []) and s.prog in _NETWORK_PROGS:
            return deny("read-only-agent",
                        f"The {ctx.agent_type} agent is read-only and has no network access; `{s.prog}` is not available to it.")
        if s.argv and ("$" in s.argv[0] or "`" in s.argv[0]):
            return deny("opaque-write",
                        f"The command name here is computed at run time ({s.argv[0]}), so the gates cannot tell what runs. "
                        "Write the command out literally.")
        if _launches_claude(s):
            return deny("nested-agent",
                        "Starting another Claude Code session from an agent session is not allowed: it would run outside "
                        "this session's audit trail and its prompt would look like a human's. Use a subagent instead.")
        if s.prog in ("cd", "pushd") and len(s.argv) > 1 and not s.argv[1].startswith("-"):
            nxt = os.path.expanduser(s.argv[1])
            cwd = os.path.realpath(nxt if os.path.isabs(nxt) else os.path.join(cwd, nxt))
            continue
        d = _check_script(ctx, cmdparse.script_execution(s), cwd)
        if d is None:
            for a in s.argv[1:]:
                # `make -f /tmp/x`, `xcrun swift /tmp/x`, `go run /tmp/x.go`: a program from a temp directory
                if a.startswith(tuple(_TMP_DIRS)) or a.startswith(os.path.realpath(os.environ.get("TMPDIR", "/tmp"))):
                    d = _check_script(ctx, a, cwd)
                    if d is not None:
                        break
        if d is not None:
            return d
        if _is_evidence_cli(s):
            args = [a for a in s.argv[1:] if not a.startswith("-")]
            if s.prog != "evidence":
                args = args[1:]
            github_recorded = args[:1] == ["approve"] and any(a.startswith("--github-pr") for a in s.argv)
            if (args[:1] == ["approve"] and not github_recorded) or args[:2] in (["change", "set-tier"], ["change", "release"], ["change", "clear-violations"]):
                return deny("self-approval",
                            "Approving a plan (and changing a change's tier) is a human action. Ask the human to run "
                            f"`/evidence-sdlc:approve <KEY> <plan-sha>` in the Claude Code prompt, or `evidence {' '.join(args[:2])} …` in "
                            "their own terminal. (Recording an approval a human already gave on GitHub, with "
                            "`evidence approve <KEY> --github-pr <N>`, is allowed.)")
        if s.prog == "git":
            d = _check_git(ctx, s, bodies)
            if d is not None:
                return d
        elif s.prog == "gh":
            d = _check_gh(ctx, s)
            if d is not None:
                return d
        d = _check_http(ctx, s) or _check_deploy(ctx, s)
        if d is not None:
            return d
        writes = cmdparse.writes_of(s)
        for var, val in s.env.items():
            # `JUNIT_OUT=validation/results/x.xml pytest`: a path handed to a program to write
            if "/" in val and not val.startswith(("http:", "https:", "/dev/")) and re.search(r"(OUT|OUTPUT|FILE|PATH|DIR|DEST|REPORT|LOG)", var):
                writes.append(cmdparse.Write(val, "write", f"{var}= output path"))
        extra = cmdparse.stdin_code_writes(s, bodies) or cmdparse.stdin_code(s)
        if extra:
            writes.append(extra)
        for w in writes:
            if w.path is None:
                d = _check_opaque(ctx, w)
            else:
                if w.path.startswith(("$", "`")) or "$(" in w.path:
                    d = deny("opaque-write",
                             f"This command writes to a path computed at run time ({w.path}), which the gates cannot "
                             "check. Write to a literal path, or use the Edit/Write tools.")
                else:
                    content = "\n".join(bodies) if w.detail == "redirect" else None
                    d = None
                    for target in _expand(w.path, cwd):
                        full = os.path.join(cwd, os.path.expanduser(target)) if not os.path.isabs(os.path.expanduser(target)) else target
                        rel, _real = st.normalize(full, cwd, ctx.root)
                        if rel is not None and (rel == "" or os.path.isdir(full)):
                            d = _dir_problem(ctx, rel)
                            if d is not None:
                                break
                        d = check_write(ctx, full, content=content, kind=w.kind, detail=w.detail)
                        if d is not None and not d.allow:
                            break
            if d is not None and not d.allow:
                if w.path is not None:
                    d.reason = f"[via Bash: {w.detail}] " + d.reason
                return d
    return ALLOW


_GIT_OPAQUE = ("git reset --hard", "git clean -f", "git stash pop", "git stash apply")


def _check_opaque(ctx, w):
    pol = ctx.policy
    if w.detail in _GIT_OPAQUE:
        # Restores committed content rather than authoring new content; allowed
        # only inside an approved change (same bar as any source write).
        d = check_gated(ctx, None, "write", w.detail)
        return d if not d.allow else None
    if pol.get("deny_opaque_writes", True):
        return deny("opaque-write",
                    f"This command modifies files in a way the gates cannot inspect ({w.detail}). Use the Edit or Write "
                    "tools for file changes so the plan, claims, test-protection and secret checks can run.")
    return None


# ------------------------------------------------------------------ entry points

def edit_content(tool, ti):
    if tool == "Write":
        return ti.get("content") or ""
    if tool == "Edit":
        return ti.get("new_string") or ""
    if tool == "MultiEdit":
        return "\n".join((e or {}).get("new_string", "") for e in ti.get("edits") or [])
    if tool == "NotebookEdit":
        return ti.get("new_source") or ""
    return ""


def decide_pre(ctx):
    tool, ti = ctx.tool, ctx.tool_input
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = ti.get("file_path") or ti.get("notebook_path") or ti.get("path")
        if not path:
            return deny("malformed", f"{tool} call has no file path; refusing rather than guessing.")
        return check_write(ctx, path, content=edit_content(tool, ti))
    if tool in ("Read", "Grep", "Glob"):
        p = ti.get("file_path") or ti.get("path") or ""
        real = os.path.realpath(os.path.expanduser(p)) if p else ""
        if re.search(r"^/proc/[^/]+/environ|/Library/Application Support/ClaudeCode|^/etc/claude-code|managed-settings\.json$", real):
            return deny("secret-access", "Managed settings and process environments are not readable by an agent session.")
        return ALLOW
    if tool == "Bash":
        cmd = ti.get("command")
        if not isinstance(cmd, str):
            return deny("malformed", "Bash call has no command string; refusing rather than guessing.")
        return check_bash(ctx, cmd)
    return ALLOW
