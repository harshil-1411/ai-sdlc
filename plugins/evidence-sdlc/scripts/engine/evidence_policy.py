"""Evidence Chain gate engine: every PreToolUse decision in one place.

decide_pre(ctx) returns a Decision. The hook shell (hook.py) handles I/O and fails
closed on any error. Rules are driven by the merged policy (state.load_policy)
and the active change's state (.evidence/changes/<KEY>/).
"""
import fnmatch
import json
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
    if not signing.enabled() and int(state.get("tier") or 1) > int(pol.get("unsigned_max_tier", 1)):
        return deny("unsigned-mode",
                    f"{what}: change {key} is Tier {state.get('tier')}, and this session has no signing key "
                    "(UNSIGNED MODE), so its approval and records could be forged. The organisation deploys "
                    "EVIDENCE_SIGNING_KEY (see docs/managed-settings.md), or sets unsigned_max_tier in its org policy.")
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
    serious = [v for v in st.open_violations(ctx.root, key, ctx.branch)
               if v.get("rule") in ("hidden-change", "control-plane", "audit-tamper", "integrity-snapshot-missing",
                                    "integrity-snapshot-altered", "integrity-snapshot-replayed")]
    if serious:
        return deny("integrity-violation",
                    f"{what}: the integrity monitor recorded {len(serious)} change(s) to git metadata or the control "
                    f"plane ({', '.join(sorted({v['path'] for v in serious})[:4])}). Source edits are paused until a human "
                    f"reviews and runs `evidence change clear-violations {key}`.")
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
    if (tier >= 3 and pol.get("tier3_distinct_approver", True) and approval.get("method") in ("prompt", "tty")
            and state.get("created_by") and approval.get("approver") == state.get("created_by")):
        return deny("tier3-same-person",
                    f"{what}: change {key} is Tier 3, and its plan was approved by the same person who started the "
                    f"change ({approval.get('approver')}). Tier 3 needs a second person: another engineer approves "
                    "in their own session or terminal, or the plan is approved on GitHub.")
    if tier >= 3 and pol.get("deny_tier3_auto_modes", True) and ctx.permission_mode in pol.get("tier3_denied_permission_modes", []):
        why = _tier3_gate_problem(ctx)
        if why:
            return deny("tier3-auto-mode",
                        f"{what}: change {key} is Tier 3, which requires per-change human review, but this session is in "
                        f"'{ctx.permission_mode}' mode. Switch to the default permission mode for Tier 3 work. {why}")
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


# ------------------------------------------------------------------ server gate (REQ-LLA-08, 09)

CI_GATE_APP_ID = 15368  # the GitHub Actions app [NEEDS VERIFICATION against a captured response]
CI_GATE_FAIL_SECONDS = 60
CI_GATE_BUDGET_SECONDS = 15  # all gh calls on a cache miss, inside the hook's 25 s budget


def _ci_gate_cache_rel(root):
    import hashlib
    return "evidence-chain-ci-gate/" + hashlib.sha256(root.encode()).hexdigest()[:16] + ".json"


def _github_slug(url):
    """owner/name (lower case) for a github.com URL over https, ssh or scp-style ssh, with or
    without `.git`; None for anything else."""
    m = (re.fullmatch(r"(?i)https://(?:[^@/\s]+@)?github\.com(?::443)?/([^/\s]+)/([^/\s]+?)(?:\.git)?/?", url)
         or re.fullmatch(r"(?i)ssh://(?:git@)?github\.com(?::22)?/([^/\s]+)/([^/\s]+?)(?:\.git)?/?", url)
         or re.fullmatch(r"(?i)(?:git@)?github\.com:([^/\s]+)/([^/\s]+?)(?:\.git)?/?", url))
    if not m or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", g) for g in m.groups()):
        return None
    return f"{m.group(1)}/{m.group(2)}".lower()


def _scoped(root, key):
    """[(scope, value)] for every setting of `key`, with its scope; [] when there is none."""
    out = st.run_git(["config", "--show-scope", "--get-all", key], root) or ""
    return [tuple(l.split("\t", 1)) for l in out.splitlines() if "\t" in l]


def _origin_repo(root):
    """owner/name of the repository's `origin` remote, read from the repository's own config only
    (H1, re-review H-A): exactly one local remote.origin.url on github.com; remote.origin.pushurl
    absent or equal to it; no remote.origin.url/pushurl at another scope (global, system,
    worktree, command) and no url.*.insteadOf / pushInsteadOf rewrite anywhere. None otherwise."""
    urls, pushes = _scoped(root, "remote.origin.url"), _scoped(root, "remote.origin.pushurl")
    if any(sc != "local" for sc, _ in urls + pushes) or len(urls) != 1:
        return None
    if any(v != urls[0][1] for _, v in pushes):
        return None
    rewrites = st.run_git(["config", "--get-regexp", r"^url\..*\.(insteadof|pushinsteadof)$"], root)
    if rewrites:
        return None
    return _github_slug(urls[0][1].strip())


def _gh_config_problem():
    """Why the gh configuration cannot be trusted for gate detection, or None (H2, re-review H-B).
    Deliberately crude, so that no YAML spelling gets past it: any mention of http_unix_socket in
    config.yml or hosts.yml (quoted, flow style, even a comment) refuses, as does any host-like
    name in hosts.yml other than github.com, any read error, and a config directory (or
    GH_CONFIG_DIR / XDG_CONFIG_HOME) that is a symlink leading outside $HOME."""
    home = os.path.realpath(os.path.expanduser("~"))
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = os.environ.get("GH_CONFIG_DIR") or os.path.join(xdg or os.path.expanduser("~/.config"), "gh")
    for d in filter(None, (os.environ.get("GH_CONFIG_DIR"), xdg, base)):
        if os.path.islink(d) or os.path.realpath(d) != os.path.abspath(d):
            real = os.path.realpath(d)
            if real != home and not real.startswith(home + os.sep):
                return f"the gh configuration directory {d} is a symlink leading outside the home directory"
    for name in ("config.yml", "hosts.yml"):
        p = os.path.join(base, name)
        try:
            text = open(p, "rb").read(1 << 20).decode("utf-8", "replace")
        except FileNotFoundError:
            continue
        except OSError as e:
            return f"the gh configuration {p} could not be read ({e.strerror})"
        if "http_unix_socket" in text.lower():
            return f"the gh configuration {p} mentions http_unix_socket, which could redirect the GitHub API"
        if name == "hosts.yml":
            names = {h.lower() for h in re.findall(r"[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}", text)}
            other = sorted(h for h in names if h != "github.com")
            if other:
                return f"the gh configuration {p} names a host other than github.com ({other[0][:60]})"
    return None


def _dir_not_user_writable(d):
    try:
        return os.stat(d).st_uid != os.getuid() and not os.access(d, os.W_OK)
    except OSError:
        return False


def _gate_gh(pol):
    """(path, None) for the gh the gate may run, or (None, why) (H2). The org policy's absolute
    `ci_gate_gh_path` wins; otherwise the first gh on PATH, which must be a file the session's user
    could not have written (neither it nor its directory writable by the user). EVIDENCE_GH is not
    used here."""
    import integrity
    pinned = pol.get("ci_gate_gh_path")
    if pinned:
        if not isinstance(pinned, str) or not os.path.isabs(pinned) or not os.path.isfile(pinned) \
                or not os.access(pinned, os.X_OK):
            return None, f"ci_gate_gh_path ({str(pinned)[:120]}) is not an absolute path to an executable file"
        return pinned, None
    for d in (os.environ.get("PATH") or "").split(os.pathsep):
        cand = os.path.join(d, "gh") if d and os.path.isabs(d) else None
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            real = os.path.realpath(cand)
            # the file gh resolves to, and (for a link) the directory holding the link, are both beyond the user
            link_ok = not os.path.islink(cand) or _dir_not_user_writable(os.path.dirname(cand))
            if integrity._not_user_writable(real) and link_ok:
                return real, None
            return None, (f"the first gh on PATH ({cand}) is writable by the session's user, so its answer cannot be "
                          "trusted; the organisation sets ci_gate_gh_path to a root-owned gh")
    return None, "no gh executable was found on PATH"


def _ci_gate_bind(ctx):
    pol = ctx.policy
    return {"root": ctx.root, "repo": (pol.get("approval") or {}).get("github_repo") or "",
            "origin": _origin_repo(ctx.root), "gh_path": pol.get("ci_gate_gh_path") or "",
            "check": pol.get("ci_gate_check", "verify-range"), "app_id": pol.get("ci_gate_app_id", CI_GATE_APP_ID),
            "enforce_admins": bool(pol.get("ci_gate_require_enforce_admins", False)),
            "ttl": int(pol.get("ci_gate_cache_seconds", 900))}


def _ci_gate_cache_read(ctx, bind):
    """The cached (confirmed, why, evidence), or None when there is no usable cache: unsigned,
    altered, a link or non-file, bound to other values, from the future or expired."""
    import signing
    import tempfile
    import time
    try:
        obj = json.loads(st.read_file_nofollow(tempfile.gettempdir(), _ci_gate_cache_rel(ctx.root), 64 * 1024))
    except (OSError, ValueError):
        return None
    if not isinstance(obj, dict) or signing.verify(obj) is not True or obj.get("bind") != bind:
        return None
    at, ttl = obj.get("at"), bind["ttl"] if obj.get("confirmed") is True else CI_GATE_FAIL_SECONDS
    if not isinstance(at, (int, float)) or isinstance(at, bool) or not (0 <= time.time() - at <= ttl):
        return None
    return obj.get("confirmed") is True, str(obj.get("why") or ""), obj.get("evidence") or {}


def _ci_gate_cache_write(ctx, bind, confirmed, why, evidence):
    import signing
    import tempfile
    import time
    if not signing.enabled():
        return  # an unsigned cache could be forged, so none is written
    try:
        st.write_file(tempfile.gettempdir(), _ci_gate_cache_rel(ctx.root),
                      json.dumps(signing.sign({"bind": bind, "confirmed": bool(confirmed), "why": why,
                                               "evidence": evidence, "at": time.time()})))
    except (OSError, ValueError):
        pass


def _ci_gate_fetch(ctx, bind):
    """Read GitHub through the pinned gh: the default branch, then its classic protection and,
    if that does not confirm, its rulesets. Returns (confirmed, why, evidence); fails closed."""
    import time
    import urllib.parse
    repo, check, app = bind["repo"], bind["check"], bind["app_id"]
    gh, why_gh = _gate_gh(ctx.policy)
    if gh is None:
        return False, why_gh, {}
    why_cfg = _gh_config_problem()
    if why_cfg:
        return False, why_cfg, {}
    deadline = time.monotonic() + CI_GATE_BUDGET_SECONDS

    def api(path):
        left = deadline - time.monotonic()
        if left <= 1:
            raise RuntimeError("the time allowed for reading GitHub ran out")
        return json.loads(st.run_gh(["api", path], ctx.root, repo, timeout=min(10, left), exe=gh))

    def pinned(v):
        return isinstance(v, int) and not isinstance(v, bool) and v == app

    try:
        info = api(f"repos/{repo}")
        branch = info.get("default_branch") if isinstance(info, dict) else None
        if not isinstance(branch, str) or not branch:
            return False, f"GitHub did not report a default branch for {repo}", {}
        q = urllib.parse.quote(branch, safe="")
        b = api(f"repos/{repo}/branches/{q}")
        rsc = ((b.get("protection") or {}).get("required_status_checks") or {}) if isinstance(b, dict) else {}
        checks = [c for c in (rsc.get("checks") or []) if isinstance(c, dict) and c.get("context") == check]
        level = rsc.get("enforcement_level")
        ev = {"repo": repo, "branch": branch, "check": check, "classic": {"enforcement_level": level,
                                                                         "app_ids": [c.get("app_id") for c in checks]}}
        why = []
        if checks and level in ("non_admins", "everyone"):
            if not any(pinned(c.get("app_id")) for c in checks):
                why.append(f"`{check}` is required on {branch} but not pinned to GitHub Actions (app {app}); its "
                           "source is " + ", ".join("any source" if c.get("app_id") is None else f"app {c.get('app_id')}"
                                                    for c in checks))
            elif bind["enforce_admins"] and level != "everyone":
                why.append(f"`{check}` on {branch} is not enforced for administrators "
                           "(ci_gate_require_enforce_admins is set)")
            else:
                return True, f"`{check}` is required on {branch} by branch protection, pinned to GitHub Actions", ev
        rules = api(f"repos/{repo}/rules/branches/{q}")
        found = []
        for rule in rules if isinstance(rules, list) else []:
            if isinstance(rule, dict) and rule.get("type") == "required_status_checks":
                for c in ((rule.get("parameters") or {}).get("required_status_checks") or []):
                    if isinstance(c, dict) and c.get("context") == check:
                        found.append(c.get("integration_id"))
        ev["rulesets"] = {"integration_ids": found}
        if any(pinned(i) for i in found):
            if bind["enforce_admins"]:
                # the rules endpoint does not return a ruleset's bypass actors, so "no one bypasses" is unprovable
                why.append(f"`{check}` is required on {branch} only by a ruleset, and ci_gate_require_enforce_admins is "
                           "set: the engine cannot read a ruleset's bypass actors, so it cannot show admins are held to it")
                return False, "; ".join(why), ev
            return True, f"`{check}` is required on {branch} by a ruleset, pinned to GitHub Actions", ev
        if found:
            why.append(f"`{check}` is required on {branch} by a ruleset but not pinned to GitHub Actions (app {app})")
        if not why:
            why.append(f"`{check}` is not required on {branch} (neither branch protection nor a ruleset requires it)")
        return False, "; ".join(why), ev
    except Exception as e:  # gh missing, failing, timing out, non-JSON: not confirmed, never an error
        return False, f"GitHub could not be read through gh ({type(e).__name__}: {str(e)[:160]})", {}


TIER3_NEVER_GATE_MODES = ("bypassPermissions", "dontAsk")


def _tier3_gate_problem(ctx):
    """None when a Tier 3 edit in this permission mode is allowed because the server gate is
    confirmed (REQ-LLA-08); otherwise the missing condition, with the owner action."""
    import signing
    pol, mode = ctx.policy, ctx.permission_mode
    allowed = pol.get("tier3_gate_allowed_modes", ["acceptEdits", "auto"])
    if mode in TIER3_NEVER_GATE_MODES or not isinstance(allowed, list) or mode not in allowed:
        return f"'{mode}' is never allowed for Tier 3, whatever the server gate."
    if pol.get("tier3_auto_modes_with_required_gate", True) is not True:
        return ("The org policy sets tier3_auto_modes_with_required_gate to false (a repository policy can only "
                "switch it off), so Tier 3 is not allowed in this mode.")
    if not signing.enabled():
        return ("This session has no signing key (UNSIGNED MODE), so the server-gate check cannot be cached "
                "safely and Tier 3 is not allowed in this mode.")
    ok, why, _ = _ci_gate(ctx)
    if ok:
        return None
    return (f"Tier 3 in this mode needs the server gate confirmed on GitHub, and it is not: {why}. Owner action: make "
            f"`{pol.get('ci_gate_check', 'verify-range')}` a required status check on the default branch with its "
            "source set to GitHub Actions, and set approval.github_repo in the org policy.")


def _ci_gate(ctx):
    """(confirmed, why, evidence): is `ci_gate_check` a required status check on the default branch
    of approval.github_repo, pinned to the GitHub Actions app (REQ-LLA-09)? Read from GitHub, never
    from a local assertion, and cached in a signed temp file (900 s confirmed, 60 s not)."""
    bind = _ci_gate_bind(ctx)
    if not bind["repo"]:
        return False, "approval.github_repo is not set in the org policy, so the server gate cannot be read", {}
    if bind["origin"] != bind["repo"].lower():
        # the gate confirmed is the one on approval.github_repo; it governs only a repository pushing there (H1)
        return False, (f"this repository's origin remote ({bind['origin'] or 'none on github.com'}) is not "
                       f"approval.github_repo ({bind['repo']}), so that repository's server gate does not govern it"), {}
    cached = _ci_gate_cache_read(ctx, bind)
    if cached is not None:
        return cached
    confirmed, why, ev = _ci_gate_fetch(ctx, bind)
    _ci_gate_cache_write(ctx, bind, confirmed, why, ev)
    if confirmed:
        try:
            st.audit_append(ctx.root, ctx.session, {"event": "tier3-auto-mode-allowed", "gate": ev, "why": why,
                                                    "engine": st.ENGINE_VERSION})
        except Exception:
            pass  # the audit log must never break a session; the next cache fill logs again
    return confirmed, why, ev


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


_REMOTE_CONFIG_KEYS = ("remote.*.url", "remote.*.pushurl", "url.*.insteadof", "url.*.pushinsteadof")


def _check_git(ctx, s, bodies=()):
    pol = ctx.policy
    gopts, sub, sargs = cmdparse.git_split(s.argv)
    for opt, val in gopts:
        if opt == "-c" and val and any(fnmatch.fnmatch(val.split("=", 1)[0].lower(), g) for g in _REMOTE_CONFIG_KEYS):
            return deny("remote-change", "`git -c` on a remote URL or URL rewrite repoints where git talks to; "
                                         "a human changes remotes.")
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
    if sub == "config" and any(a.lower().startswith(("user.", "author.", "committer.")) for a in sargs) and not any(
            a in ("--get", "--get-all", "--list", "-l", "--get-regexp") for a in sargs):
        return deny("identity", "Changing git identity (user.*, author.*, committer.*) is a human action: approval and "
                                "Tier 3 second-person checks rely on it.")
    if any(v and v.split("=", 1)[0].lower().startswith(("user.", "author.", "committer.")) for o, v in gopts if o == "-c"):
        return deny("identity", "`git -c user.*=…` changes your git identity; not available to an agent session.")
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
        named = setting[1:] if setting[:1] in (["set"], ["unset"], ["get"]) and len(setting) > 1 else setting
        if named and not readonly and setting[:1] != ["get"] and any(
                fnmatch.fnmatch(named[0].lower(), g) for g in _REMOTE_CONFIG_KEYS):
            # re-review H-A: where origin points decides which server gate governs this repository
            return deny("remote-change",
                        f"Setting git config '{named[0]}' repoints a remote (or rewrites where git pushes), at any scope; "
                        "the server gate the engine reads depends on it. A human changes remotes.")
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


AUDIT_TAIL_MAX = 2  # entries the engine itself appends between `git add` and `git commit`


def _log_tail_only(root, rel):
    """True when the working audit log is the staged one plus at most AUDIT_TAIL_MAX appended
    lines. The engine appends to the session log on every tool call, including the call that
    staged it, so an exact match is impossible; an altered, truncated or long-unstaged log
    still fails."""
    staged = st.run_git(["show", f":{rel}"], root, timeout=20, text=False)
    if staged is None:
        return False
    try:
        current = open(os.path.join(root, rel), "rb").read()
    except OSError:
        return False
    if not current.startswith(staged) or (staged and not staged.endswith(b"\n")):
        return False
    tail = current[len(staged):].decode("utf-8", "replace").splitlines()
    if len(tail) > AUDIT_TAIL_MAX:
        return False
    # Only the engine's own after-the-call entries may be left for the next commit; a deny or a
    # violation must go into this one (staging an older prefix cannot hide it).
    session = os.path.basename(rel)[:-len(".jsonl")]
    import signing
    try:
        prev = json.loads(staged.decode("utf-8", "replace").splitlines()[-1]).get("hash", "") if staged else ""
    except (ValueError, IndexError):
        return False
    for line in tail:
        try:
            e = json.loads(line)
        except ValueError:
            return False
        if e.get("event") != "tool" or re.sub(r"[^A-Za-z0-9_-]", "_", str(e.get("session")))[:80] != session:
            return False
        # an entry edited in place (a deny turned into a "tool") breaks its hash or signature
        if e.get("prev") != prev or st.entry_hash(e, prev) != e.get("hash") or signing.verify(e) is False:
            return False
        prev = e.get("hash")
    return True


# `git commit` options that take the next argument as their value (so it is not a pathspec)
_COMMIT_VALUE_OPTS = {"-m", "--message", "-F", "--file", "-C", "-c", "--reuse-message", "--reedit-message", "--author",
                      "--date", "--cleanup", "--trailer", "--fixup", "--squash", "-t", "--template", "--pathspec-from-file"}
# git subcommands that change the index; combined with a commit in one command they change what
# is committed after the gate looked at it (REQ-IMH-10)
_INDEX_CHANGING = {"add", "rm", "mv", "reset", "restore", "checkout", "switch", "stash", "update-index", "read-tree",
                   "apply", "am", "merge", "cherry-pick", "revert", "pull", "rebase"}
_INDEX_ENV = ("GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES")


def _commit_bypass(sargs):
    """The `git commit` forms that commit something other than the index the gate checked:
    a pathspec, --only, --include, --patch, --interactive, --pathspec-from-file (REQ-IMH-10)."""
    found, i = [], 0
    while i < len(sargs):
        a = sargs[i]
        if a == "--":
            if sargs[i + 1:]:
                found.append("a pathspec")
            break
        if a in _COMMIT_VALUE_OPTS:
            if a == "--pathspec-from-file":
                found.append(a)
            i += 2
            continue
        name = a.split("=", 1)[0]
        # git accepts any unambiguous prefix of a long option (--patc, --pathspec-from-f=…)
        long_hit = next((o for o in ("--only", "--include", "--patch", "--interactive", "--pathspec-from-file")
                         if name.startswith("--") and len(name) > 3 and o.startswith(name)), None)
        if long_hit:
            found.append(long_hit)
            if long_hit == "--pathspec-from-file" and "=" not in a:
                i += 2
                continue
        elif re.fullmatch(r"-[A-Za-z]+", a):
            letters = a[1:]
            # value-taking letters end the cluster: -am 'msg', -uno, -Skeyid
            for n, ch in enumerate(letters):
                if ch in "oip":
                    found.append(f"-{ch}")
                if ch in "mFCctuS":
                    if ch in "mFCct" and n == len(letters) - 1:
                        i += 1  # its value is the next argument
                    break
        elif not a.startswith("-") and a:
            found.append("a pathspec")
        i += 1
    return found


def _check_commit(ctx, sargs, bodies=()):
    pol = ctx.policy
    bypass = _commit_bypass(sargs)
    if bypass:
        return deny("commit-bypass",
                    f"`git commit` with {', '.join(dict.fromkeys(bypass))} commits files other than the staged index "
                    "the gates check. Stage exactly what you mean to commit with `git add` (as its own command), then "
                    "run a plain `git commit -m …`.")
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
    git_failed = deny("git-unavailable", "git could not list what this commit contains, so it cannot be checked. "
                                         "Try again; if it persists a human checks the repository.")
    if key and pol.get("commit_requires_audit", True):
        # a failed git call is never "nothing staged" (REQ-IMH-23)
        staged, tracked, unstaged = (st.git(a, ctx.root) for a in (["diff", "--cached", "--name-only"],
                                                                   ["ls-files", ".evidence"], ["diff", "--name-only"]))
        if staged is None or tracked is None or unstaged is None:
            return git_failed
        staged, tracked, unstaged = set(staged.split()), set(tracked.split()), set(unstaged.split())
        need = []
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", ctx.session or "")[:80]
        session_log = f".evidence/audit/{safe}.jsonl"
        for rel in (session_log, f".evidence/changes/{key}/state.json",
                    f".evidence/changes/{key}/approval.json", f".evidence/audit/approval-{key}.jsonl"):
            if not os.path.isfile(os.path.join(ctx.root, rel)):
                continue
            if rel not in staged and rel not in tracked:
                need.append(rel)
            elif rel in unstaged and not (rel == session_log and _log_tail_only(ctx.root, rel)):
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
        diffs = [st.git(["diff", "--cached", "-U0", "--no-color"], ctx.root, timeout=20)]
        if "all" in flags:
            diffs.append(st.git(["diff", "-U0", "--no-color"], ctx.root, timeout=20))
        if any(d is None for d in diffs):
            return git_failed
        diff = "".join(diffs)
        added = "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
        d = _secret_decision(ctx, added, "the staged changes")
        if d is not None:
            return d
        d = _secret_decision(ctx, msg, "the commit message")
        if d is not None:
            return d
    return None


_DISPATCH_DENIED = ("Dispatching a workflow from another ref is a human action: it runs that branch's own workflow "
                    "file with the repository's secrets, and could post a check under the merge gate's name. To "
                    "re-check a pull request, a human re-runs its `verify-range` job from the PR's checks.")


_GH_VALUE_FLAGS = {"-R", "--repo", "-H", "--header", "-F", "-f", "--field", "--raw-field", "--input", "-X", "--method",
                   "--jq", "-q", "-t", "--template"}


def _gh_words(args):
    """gh's positional words: flags dropped, and the value of a value-taking flag dropped with it
    (so `gh run -R o/r rerun 42` reads as run rerun 42)."""
    words, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a in _GH_VALUE_FLAGS:
            skip = True
            continue
        if not a.startswith("-"):
            words.append(a)
    return words


def _check_gh(ctx, s):
    pol = ctx.policy
    args = s.argv[1:]
    words = _gh_words(args)
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
            elif a.startswith("-X") and len(a) > 2:
                method = a[2:].lstrip("=").upper()
        override = None
        for i, a in enumerate(args):
            hv = args[i + 1] if a in ("-H", "--header") and i + 1 < len(args) else (
                a.split("=", 1)[1] if a.startswith("--header=") else (a[2:] if a.startswith("-H") and len(a) > 2 else None))
            if hv and re.match(r"(?i)\s*x-http-method-override\s*:", hv):
                override = hv.split(":", 1)[1].strip().upper() or "POST"
        endpoint = next((w for w in words[1:] if "/" in w), "")
        # REQ-LLA-10: a required check matched by name can be satisfied by a commit status or a check run
        # anyone with the token can post; the authority is the app pin (ADR-0005), this is early feedback.
        fields = any(a in ("-f", "-F", "--field", "--raw-field", "--input") or a.startswith(("-f", "-F", "--field=",
                                                                                               "--raw-field=", "--input="))
                     for a in args)

        def _norm(w):  # percent-encoding and doubled slashes are resolved before matching (L1)
            import urllib.parse
            for _ in range(3):
                w = urllib.parse.unquote(w)
            return re.sub(r"/{2,}", "/", w)
        targets = [_norm(w) for w in words[1:]]
        writes = method in ("POST", "PATCH", "PUT") or override is not None or (method is None and fields)
        if writes and any(re.search(r"/statuses/[^/\s]|/check-runs\b|/check-suites\b|/actions/(?:runs|jobs)/[^/\s]+/rerun", w)
                          for w in targets):
            return deny("check-forgery",
                        "Creating or updating a commit status or check run (or re-running a workflow) from an agent "
                        "session is not allowed: a required check matched by name could be satisfied that way. CI posts "
                        "checks; reading them is fine.")
        if "graphql" in words and any(a == "--input" or a.startswith("--input=")
                                      or re.search(r"^(?:-[Ff]|--field=|--raw-field=)?query=@", a) for a in args):
            return deny("check-forgery", "`gh api graphql` with the query read from a file or --input hides what it does "
                                         "(it could create a check run); pass the query inline.")
        if method in ("PUT", "POST", "PATCH", "DELETE") and re.search(r"/merge\b|/protection\b|/rulesets\b|/branches/[^/]+/rename|/git/refs", endpoint):
            return deny("agent-merge",
                        f"`gh api -X {method} {endpoint}` changes merges, branch protection or refs. That is a human action.")
        if method is None and re.search(r"/merge\b", endpoint) and any(a in ("-f", "-F", "--field", "--raw-field", "--input") for a in args):
            return deny("agent-merge", "`gh api` with fields against a /merge endpoint is a merge; that is a human action.")
        if re.search(r"/dispatches\b", endpoint) and (method in ("POST", None)):
            return deny("workflow-dispatch", _DISPATCH_DENIED)
    if words[:2] == ["run", "rerun"]:
        return deny("check-forgery", "Re-running a workflow run from an agent session is not allowed: it can produce a "
                                     "check run under a required check's name. A human re-runs checks.")
    if words[:2] == ["workflow", "run"] and any(a.startswith(("-r", "--ref")) for a in args):  # -rX, -r=X, --ref=X
        # dispatched from another ref (a PR branch), a workflow runs that branch's own YAML with the
        # repository's secrets, and can post a check under the merge gate's name (review, ADR-0004).
        # Without --ref it runs the default branch's workflow.
        return deny("workflow-dispatch", _DISPATCH_DENIED)
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
        if "graphql" in words and re.search(r"createCheckRun|updateCheckRun|createCheckSuite|rerequestCheckSuite", joined):
            return deny("check-forgery", "This GraphQL mutation creates or updates a commit status or check run; CI posts "
                                         "checks, not an agent session.")
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
        return _release_verify(ctx, verify, approval)
    return None


def _release_verify(ctx, verify, approval):
    """The org policy's release-approval check: an org-configured command, run without the
    signing key or GIT_* in its environment (REQ-IMH-22)."""
    try:
        r = subprocess.run(verify.replace("{approval}", approval), shell=True, cwd=ctx.root, env=st._child_env(),
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return deny("release-approval",
                        f"Release approval '{approval}' could not be verified by the policy's check "
                        f"({r.stderr.strip()[:200] or 'non-zero exit'}).")
    except (OSError, subprocess.TimeoutExpired) as e:
        return deny("release-approval", f"Release approval verification failed to run: {e}.")
    return None


_KNOWN_PROGS = set(cmdparse.READ_ONLY_PROGS) | cmdparse.WRITE_PROGS | cmdparse.INTERPRETERS | cmdparse.SHELLS | {
    "git", "gh", "evidence", "cd", "pwd", "true", "false", "sleep", "date", "which", "command", "type", "mkdir", "find",
    "xargs", "tr", "tee", "env", "export", "npm", "npx", "pnpm", "yarn", "node", "pytest", "tox", "make", "cargo", "go",
    "mvn", "gradle", "dotnet", "rustc", "javac", "java", "ruff", "black", "eslint", "prettier", "tsc", "jest", "vitest",
    "playwright", "pip", "pip3", "uv", "poetry", "bundle", "rake", "rspec", "docker", "kubectl", "helm", "terraform"}
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


ENGINE_LIFECYCLE = (["change", "start"], ["change", "advance"])


def lifecycle_call(ctx, cmd):
    """Classify a Bash command that runs `evidence change start|advance`.

    Returns None when it does not, ("run", argv, cwd) when it is the whole command (after any
    `cd` glue), and ("chained", None, None) otherwise. The hook performs "run" itself, with the
    engine's own code and signing key, because the agent's shell cannot see the key and would
    write unsigned state that a signed deployment rejects."""
    simples, ok, _ = cmdparse.split_simple(cmd)
    found, other = [], False
    cwd = ctx.cwd
    for s in simples:
        if _is_evidence_cli(s):
            args = [a for a in s.argv[1:] if not a.startswith("-")]
            if s.prog != "evidence":
                args = args[1:]
            if args[:2] in ENGINE_LIFECYCLE:
                found.append((s, cwd))
                continue
        if s.prog == "cd" and len(s.argv) == 2 and not s.env:
            nxt = os.path.expanduser(s.argv[1])
            cwd = os.path.realpath(nxt if os.path.isabs(nxt) else os.path.join(cwd, nxt))
            continue
        other = True
    if not found:
        return None
    s, cwd = found[0]
    if len(found) > 1 or other or not ok or s.env or s.piped_in:
        return ("chained", None, None)
    # The hook signs what it writes, so it only acts in the session's own repository. Claude Code
    # sets CLAUDE_PROJECT_DIR for hooks; the agent cannot move it, unlike the call's cwd.
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project or st.repo_root(cwd) != ctx.root or ctx.root != st.repo_root(os.path.realpath(project)):
        return ("elsewhere", None, None)
    argv = s.argv[1:] if s.prog == "evidence" else s.argv[2:]
    # Only `change start KEY --tier N --kind K` and `change advance KEY STAGE`: the hook is not
    # sandboxed, so it writes nothing but .evidence/changes/<KEY>/state.json.
    rest, i = [], 2
    while i < len(argv):
        a = argv[i]
        if argv[1] == "start" and a in ("--tier", "--kind") and i + 1 < len(argv):
            i += 2
            continue
        if argv[1] == "start" and re.fullmatch(r"--(tier|kind)=\S+", a):
            i += 1
            continue
        if a.startswith("-"):
            return ("options", None, None)
        rest.append(a)
        i += 1
    if len(rest) != (1 if argv[1] == "start" else 2):
        return ("options", None, None)
    if not st.SAFE_KEY.fullmatch(rest[0]) or not re.fullmatch(ctx.policy["key_pattern"], rest[0]):
        return ("badkey", None, None)
    return ("run", argv, ctx.root)


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
    git_subs = [cmdparse.git_split(s.argv)[1] for s in simples if s.prog == "git"]
    if "commit" in git_subs and any(g in _INDEX_CHANGING for g in git_subs):
        # the gate checks the index as it is now; the other command would change it before the commit runs
        return deny("commit-bypass",
                    "Run `git commit` as its own command: combined with "
                    f"`git {next(g for g in git_subs if g in _INDEX_CHANGING)}` it would commit an index the gates never "
                    "saw. Stage first, then commit in a separate call.")
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
        if pol.get("unknown_programs") == "deny" and s.argv and s.prog not in _KNOWN_PROGS and s.prog not in set(pol.get("known_programs", [])):
            return deny("unknown-program",
                        f"`{s.prog}` is not on this organisation's list of known programs (strict mode), so what it "
                        "writes cannot be judged. Ask the platform team to add it to known_programs.")
        spoof = [k for k in s.env if k.startswith(("GIT_CONFIG_", "GIT_AUTHOR_", "GIT_COMMITTER_"))
                 or k in ("EMAIL", "GIT_DIR", "GIT_WORK_TREE") + _INDEX_ENV]
        if spoof:
            return deny("identity",
                        f"Setting {', '.join(sorted(spoof)[:3])} on a command changes your git identity (who git and the "
                        "approval records think you are) or which repository is used. Not available to an agent session.")
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
