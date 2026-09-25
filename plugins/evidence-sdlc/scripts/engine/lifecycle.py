"""`evidence change|approve|audit|metrics` — the lifecycle half of the CLI.

Shares state.py with the gate engine so both read the same truth. Human-only
operations (approve, set-tier, release) refuse to run inside an agent's shell:
they need a controlling terminal and no CLAUDECODE marker, or they go through a
channel the model cannot forge (the UserPromptSubmit hook, or a GitHub review).
"""
import argparse
import base64
import getpass
import json
import os
import re
import socket
import subprocess
import sys

import state as st

AGENT_ADVANCE = {"spec", "plan", "failing-test", "verified"}


class HumanOnly(Exception):
    pass


class _Tty:
    """The controlling terminal as separate read and write text streams. A terminal is not
    seekable, and Python refuses a read-write text stream ("r+") on one."""

    def __init__(self, path):
        self.r = open(path, "r")
        try:
            self.w = open(path, "w")
        except OSError:
            self.r.close()
            raise

    def write(self, s):
        self.w.write(s)

    def flush(self):
        self.w.flush()

    def readline(self):
        return self.r.readline()


def _human_tty(path="/dev/tty"):
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        raise HumanOnly("this runs inside a Claude Code session")
    try:
        return _Tty(path)
    except OSError:
        raise HumanOnly("there is no terminal to confirm on")


def _require_key_if_signed(root, what):
    """A signed deployment rejects unsigned records, so a human action from a terminal without
    the key would write something the gates then refuse. Stop before writing it."""
    import glob
    import signing
    if signing.enabled():
        return
    ev = os.path.join(root, ".evidence")
    for p in (glob.glob(os.path.join(ev, "changes", "*", "state.json")) + glob.glob(os.path.join(ev, "changes", "*", "approval.json"))
              + glob.glob(os.path.join(ev, "changes", "*", "violations.json")) + glob.glob(os.path.join(ev, "violations", "*"))):
        try:
            if "sig" in json.load(open(p)):
                break
        except (OSError, ValueError):
            continue
    else:
        return
    sys.exit(f"`{what}` would write an unsigned record, but this repository's records are signed, so the gates would "
             "reject it. Supply the signing key to this one command without printing it, e.g.\n"
             "  export EVIDENCE_SIGNING_KEY=\"$(python3 -c 'import json; print(json.load(open(\"/Library/Application "
             "Support/ClaudeCode/managed-settings.json\"))[\"env\"][\"EVIDENCE_SIGNING_KEY\"])')\"\n"
             f"  {what} …; unset EVIDENCE_SIGNING_KEY\n"
             "(on Linux the file is /etc/claude-code/managed-settings.json). To approve a plan, sending "
             "`/evidence-sdlc:approve <KEY> <plan-sha>` in the Claude Code prompt needs no key.")


def _artifact_path(root, policy, p):
    """An --intent/--spec/--plan path: a Markdown file inside the repository, outside the
    control plane and .git. It is written by --quick and recorded in signed state."""
    rel = os.path.relpath(os.path.realpath(os.path.join(root, p)), os.path.realpath(root))
    low = rel.lower()  # macOS and Windows filesystems are case-insensitive: .Claude/ is .claude/
    if (os.path.isabs(p) or rel == ".." or rel.startswith(".." + os.sep) or not low.endswith(".md")
            or low.split(os.sep)[0] in (".git", ".evidence", ".claude")
            or st.glob_match(low, [g.lower() for g in policy.get("control_plane", [])])):
        sys.exit(f"'{p}' is not allowed as an artifact path: use a .md file inside the repository, outside "
                 ".git/, .evidence/ and .claude/.")
    return rel


def _hist(h):
    """A history entry; when the gate engine's hook performed the call for an agent, say so."""
    via = os.environ.get("EVIDENCE_LIFECYCLE_VIA", "")
    if via.startswith("hook:"):
        h.update(via="hook", session=via[5:])
    return h


def _who(root):
    email = st.git(["config", "user.email"], root)
    return (email or "").strip() or os.environ.get("USER") or getpass.getuser()


def _ctx():
    root = st.repo_root(os.getcwd())
    return root, st.load_policy(root)


def _key_arg(args, root, policy):
    if getattr(args, "key", None):
        if not st.SAFE_KEY.fullmatch(args.key) or not re.fullmatch(policy["key_pattern"], args.key):
            sys.exit(f"'{args.key}' does not look like a tracker key (pattern {policy['key_pattern']}; letters, digits, "
                     "'-' and '_' only).")
        return args.key
    key, src = st.active_key(root, policy)
    if not key:
        sys.exit(f"No change key given and none found ({src}).")
    return key


def _rel(root, p):
    return os.path.relpath(p, root) if p else None


# ------------------------------------------------------------------ status

def status_dict(root, policy, key):
    state = st.load_state(root, key)
    if not state:
        return {"key": key, "exists": False}
    tier = int(state.get("tier") or 1)
    arts = {}
    for a in ("intent", "spec", "plan"):
        arts[a] = _rel(root, st.find_artifact(root, key, a, state))
    missing = [a for a in st.required_artifacts(tier) if not arts.get(a)]
    plan = st.find_artifact(root, key, "plan", state)
    problems = st.plan_problems(plan) if plan else ["no plan"]
    approval = st.load_approval(root, key)
    prob = st.approval_problem(root, key, approval, plan) if plan else "no plan"
    if not approval:
        appr = "missing"
    elif prob is None:
        appr = "valid"
    elif prob == "approval-stale":
        appr = "stale (plan changed after approval)"
    else:
        appr = f"invalid ({prob})"
    req = policy.get("required_agents", {}).get(str(tier), [])
    done = st.recorded_agents(root, key)
    return {
        "key": key, "exists": True, "tier": tier, "kind": state.get("kind"), "stage": state.get("stage"),
        "artifacts": arts, "missing_artifacts": missing, "plan_problems": problems if plan else [],
        "plan_sha256": st.sha256_file(plan) if plan else None,
        "approval": appr, "approver": (approval or {}).get("approver"), "approval_method": (approval or {}).get("method"),
        "required_agents": req, "recorded_agents": sorted(done), "missing_agents": [a for a in req if a not in done],
        "fix_base": state.get("fix_base"), "overlaps": claim_overlaps(root, key),
        "open_violations": st.open_violations(root, key, st.current_branch(root)),
    }


def claim_overlaps(root, key):
    """Other active changes whose plan claims overlap this change's claims."""
    state = st.load_state(root, key) or {}
    plan = st.find_artifact(root, key, "plan", state)
    if not plan:
        return []
    mine = st.plan_claims(open(plan, encoding="utf-8", errors="replace").read())
    out = []
    cdir = os.path.join(root, ".evidence", "changes")
    if not os.path.isdir(cdir):
        return []
    for other in sorted(os.listdir(cdir)):
        if other == key:
            continue
        ostate = st.load_state(root, other)
        if not ostate or ostate.get("stage") == "released":
            continue
        oplan = st.find_artifact(root, other, "plan", ostate)
        if not oplan:
            continue
        theirs = st.plan_claims(open(oplan, encoding="utf-8", errors="replace").read())
        hits = sorted({a for a in mine for b in theirs if _overlap(a, b)})
        if hits:
            out.append({"change": other, "claims": hits})
    return out


def _overlap(a, b):
    def base(g):
        return re.split(r"[*?\[]", g, 1)[0].rstrip("/")
    ba, bb = base(a), base(b)
    return ba == bb or ba.startswith(bb + "/") or bb.startswith(ba + "/") or not ba or not bb


def print_status(s):
    if not s.get("exists"):
        print(f"{s['key']}: no change state. Start it with: evidence change start {s['key']} --tier <1|2|3> --kind feature|fix|chore")
        return
    print(f"{s['key']}  Tier {s['tier']}  {s['kind']}  stage: {s['stage']}")
    for a, p in s["artifacts"].items():
        need = "required" if a in [x for x in ("intent", "spec", "plan") if x in s["missing_artifacts"] or p] else ""
        print(f"  {a:7} {p or '—'}")
    if s["missing_artifacts"]:
        print(f"  MISSING for Tier {s['tier']}: {', '.join(s['missing_artifacts'])}")
    for p in s["plan_problems"]:
        print(f"  PLAN: {p}")
    print(f"  approval: {s['approval']}" + (f" (by {s['approver']} via {s['approval_method']})" if s["approver"] else ""))
    if s["plan_sha256"]:
        print(f"  plan sha256: {s['plan_sha256'][:12]}  (a human approves with: evidence approve {s['key']} {s['plan_sha256'][:12]})")
    print(f"  review agents: required {', '.join(s['required_agents']) or 'none'}; recorded {', '.join(s['recorded_agents']) or 'none'}")
    for o in s["overlaps"]:
        print(f"  OVERLAP with active change {o['change']}: {', '.join(o['claims'])} — sequence the two changes")
    nxt = next_step(s)
    if nxt:
        print(f"  next: {nxt}")


def next_step(s):
    if s["missing_artifacts"]:
        return f"write {', '.join(m + '.md' for m in s['missing_artifacts'])}"
    if s["plan_problems"]:
        return "finish the plan (Files claimed, Order of work)"
    if s["approval"] != "valid":
        return "a human approves the plan (see approval line above)"
    if s["missing_agents"]:
        return f"run review agents before push/PR: {', '.join(s['missing_agents'])}"
    return None


# ------------------------------------------------------------------ commands

def cmd_change(args):
    root, policy = _ctx()
    sub = args.change_cmd
    if sub == "list":
        cdir = os.path.join(root, ".evidence", "changes")
        rows = []
        for k in sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []:
            s = st.load_state(root, k)
            if s:
                rows.append((k, s.get("tier"), s.get("kind"), s.get("stage")))
        if args.json:
            print(json.dumps([dict(zip(("key", "tier", "kind", "stage"), r)) for r in rows], indent=2))
        else:
            for r in rows:
                print(f"{r[0]:16} Tier {r[1]}  {r[2]:8} {r[3]}")
        return 0
    key = _key_arg(args, root, policy)
    if sub == "status":
        s = status_dict(root, policy, key)
        print(json.dumps(s, indent=2)) if args.json else print_status(s)
        return 0
    if sub == "start":
        if not re.fullmatch(policy["key_pattern"], key) or not st.find_keys(key, policy):
            sys.exit(f"'{key}' does not look like a tracker key (pattern {policy['key_pattern']}).")
        if st.load_state(root, key):
            sys.exit(f"Change {key} already exists. See: evidence change status {key}")
        tier = int(args.tier)
        import signing
        cap = int(policy.get("unsigned_max_tier", 1))
        if not signing.enabled() and tier > cap:
            sys.exit(f"This session has no signing key (UNSIGNED MODE), which limits agent work to Tier {cap} changes. "
                     f"A Tier {tier} change needs EVIDENCE_SIGNING_KEY deployed (docs/managed-settings.md) or an org "
                     "policy that raises unsigned_max_tier.")
        first = {3: "intent", 2: "spec", 1: "plan"}[tier]
        state = {"key": key, "tier": tier, "kind": args.kind, "stage": first, "created_at": st.now(),
                 "created_by": _who(root), "history": [_hist({"stage": first, "at": st.now(), "by": _who(root)})]}
        for a in ("intent", "spec", "plan"):
            v = getattr(args, a, None)
            if v:
                state[a] = _artifact_path(root, policy, v)
        if getattr(args, "quick", None):
            if tier != 1 or not args.files:
                sys.exit("--quick is for Tier 1 changes and needs --files <glob> [...]")
            # the default path is checked too: a symlinked plan/ directory would otherwise lead outside
            plan_rel = _artifact_path(root, policy, state.get("plan") or f"plan/{key}.md")
            parent = os.path.join(root, os.path.dirname(plan_rel))
            os.makedirs(parent, exist_ok=True)
            if os.path.commonpath([os.path.realpath(parent), os.path.realpath(root)]) != os.path.realpath(root):
                sys.exit(f"{os.path.dirname(plan_rel)}/ leads outside the repository; --quick will not write there.")
            try:
                fd = os.open(os.path.join(root, plan_rel), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0))
            except FileExistsError:
                sys.exit(f"{plan_rel} already exists; --quick never overwrites a file.")
            with os.fdopen(fd, "w") as f:
                f.write(f"# Plan: {args.quick}\nTracker: {key}   Date: {st.now()[:10]}\nRisk tier: 1 — quick change\n\n"
                        "## Files claimed\n" + "".join(f"- `{g}`\n" for g in args.files) +
                        f"\n## Order of work\n1. {args.quick}\n2. Run the tests that cover the claimed files and the verifier.\n\n"
                        "## Proof\nThe existing tests covering the claimed files, run by the verifier.\n")
            state["plan"] = plan_rel
        st.save_state(root, key, state)
        branch = st.current_branch(root)
        print(f"Started {key}: Tier {tier}, {args.kind}. Required before source edits: "
              f"{', '.join(a + '.md' for a in st.required_artifacts(tier))}, then human approval of the plan.")
        if key not in branch and not os.environ.get("EVIDENCE_ACTIVE_CHANGE"):
            print(f"Note: the current branch '{branch}' does not carry {key}; the gates look for the key in the branch "
                  f"name. Create one, e.g.: git switch -c feature/{key}-short-name")
        for o in claim_overlaps(root, key):
            print(f"WARNING: claims overlap with active change {o['change']}: {', '.join(o['claims'])}")
        return 0
    if sub == "clear-violations":
        return _clear_violations(root, key)
    state = st.load_state(root, key)
    if not state:
        sys.exit(f"No change state for {key}. Start it with: evidence change start {key} --tier <n> --kind <kind>")
    if sub == "advance":
        import signing
        if signing.verify(state) is False:
            sys.exit(f"The change state for {key} is not signed by the gate engine, so it will not be re-signed. "
                     f"A human restarts the change (`evidence change start {key} …` with the key).")
        target = args.stage
        if target in ("approved", "released"):
            sys.exit(f"'{target}' is set by a human: approval with `evidence approve`, release with `evidence change release`.")
        if target not in AGENT_ADVANCE:
            sys.exit(f"Unknown stage '{target}'. Stages: {', '.join(st.STAGES)}")
        s = status_dict(root, policy, key)
        if target == "failing-test":
            if state.get("kind") != "fix":
                sys.exit("failing-test applies to changes started with --kind fix.")
            if s["approval"] != "valid":
                sys.exit("Approve the fix plan first (a human runs `evidence approve`).")
            head = (st.git(["rev-parse", "HEAD"], root) or "").strip()
            state["fix_base"] = head
            print(f"Fix base recorded at {head[:12]}: tests that exist at this commit are now protected from edits.")
        if target == "verified":
            if s["approval"] != "valid":
                sys.exit("Cannot mark verified: plan approval is not valid.")
            if s["missing_agents"]:
                sys.exit(f"Cannot mark verified: required review agents not recorded: {', '.join(s['missing_agents'])}.")
        if target in ("spec", "plan"):
            need = {"spec": "intent", "plan": "spec"}[target]
            if need in st.required_artifacts(state.get("tier", 1)) and not s["artifacts"].get(need):
                sys.exit(f"Cannot advance to {target}: {need}.md is required for this tier and missing.")
        state["stage"] = target
        state.setdefault("history", []).append(_hist({"stage": target, "at": st.now(), "by": _who(root)}))
        st.save_state(root, key, state)
        print(f"{key} -> {target}")
        return 0
    if sub in ("set-tier", "release", "override"):
        _require_key_if_signed(root, f"evidence change {sub}")
        try:
            tty = _human_tty()
        except HumanOnly as e:
            sys.exit(f"`evidence change {sub}` is a human action and {e}. Run it in your own terminal.")
        if sub == "set-tier":
            new = int(args.tier)
            tty.write(f"Change {key}: Tier {state.get('tier')} -> {new}. Type the new tier to confirm: ")
            tty.flush()
            if tty.readline().strip() != str(new):
                sys.exit("Not confirmed.")
            state["tier"] = new
        else:
            tty.write(f"Mark {key} released? Type the key to confirm: ")
            tty.flush()
            if tty.readline().strip() != key:
                sys.exit("Not confirmed.")
            state["stage"] = "released"
        state.setdefault("history", []).append({"stage": state["stage"], "tier": state.get("tier"), "at": st.now(),
                                                "by": _who(root), "via": "tty"})
        st.save_state(root, key, state)
        print("Recorded.")
        return 0
    return 2


def _clear_violations(root, key):
    _require_key_if_signed(root, "evidence change clear-violations")
    try:
        tty = _human_tty()
    except HumanOnly as e:
        sys.exit(f"`evidence change clear-violations` is a human action and {e}. Run it in your own terminal.")
    vs = st.open_violations(root, key, st.current_branch(root))
    if not vs:
        print("No open violations.")
        return 0
    for v in vs:
        tty.write(f"  {v.get('at')}  {v.get('path')}  ({v.get('rule')}, {v.get('action')})\n")
    tty.write(f"You reviewed these {len(vs)} change(s) and they are reverted or acceptable? Type the key to clear: ")
    tty.flush()
    if tty.readline().strip() != key:
        sys.exit("Not cleared.")
    for p in {st.violations_path(root, key, st.current_branch(root)), st.violations_path(root, None, st.current_branch(root))}:
        if os.path.isfile(p):
            data = st._read_violations(p)
            for v in data:
                if v.get("open"):
                    v.update(open=False, cleared_by=_who(root), cleared_at=st.now())
            st.write_violations(p, data, root)
    st.audit_append(root, "clear-violations", {"event": "violations-cleared", "key": key, "by": _who(root), "count": len(vs)})
    print(f"Cleared {len(vs)} violation(s).")
    return 0


def write_approval(root, key, plan, approver, method, extra=None):
    state = st.load_state(root, key) or {}
    rec = {"key": key, "plan_path": _rel(root, plan), "plan_sha256": st.sha256_file(plan), "approver": approver,
           "method": method, "approved_at": st.now(), "host": socket.gethostname()}
    rec.update(extra or {})
    import signing
    rec = signing.sign(rec)
    st.change_dir(root, key)  # validates the key
    st.write_file(root, f".evidence/changes/{key}/approval.json", json.dumps(rec, indent=2, sort_keys=True) + "\n")
    if state and state.get("stage") in ("intent", "spec", "plan"):
        state["stage"] = "approved"
        state.setdefault("history", []).append({"stage": "approved", "at": rec["approved_at"], "by": approver, "via": method})
        st.save_state(root, key, state)
    st.audit_append(root, f"approval-{key}", {"event": "approved", "key": key, "approver": approver, "method": method,
                                       "plan_sha256": rec["plan_sha256"]})
    return rec


def _preflight_approval(root, policy, key):
    state = st.load_state(root, key)
    if not state:
        sys.exit(f"No change state for {key}.")
    s = status_dict(root, policy, key)
    if s["missing_artifacts"]:
        sys.exit(f"Cannot approve {key}: missing {', '.join(s['missing_artifacts'])}.")
    if s["plan_problems"]:
        sys.exit(f"Cannot approve {key}: " + "; ".join(s["plan_problems"]))
    return st.find_artifact(root, key, "plan", state)


def cmd_approve(args):
    root, policy = _ctx()
    key = _key_arg(args, root, policy)
    if not args.github_pr:
        _require_key_if_signed(root, "evidence approve")
    plan = _preflight_approval(root, policy, key)
    sha = st.sha256_file(plan)
    if args.github_pr:
        return _approve_github(root, policy, key, plan, sha, args.github_pr)
    if policy.get("approval", {}).get("mode") == "github":
        sys.exit("Policy requires GitHub approval: an allowed approver reviews the plan on the PR, then run "
                 f"`evidence approve {key} --github-pr <N>`.")
    try:
        tty = _human_tty()
    except HumanOnly as e:
        sys.exit(f"Approval is a human action and {e}. In your own terminal run: evidence approve {key} {sha[:12]}\n"
                 f"or, in the Claude Code prompt, send the message: evidence approve {key} {sha[:12]}")
    if args.sha and not sha.startswith(args.sha.lower()):
        sys.exit(f"The plan changed: its sha256 is now {sha[:12]}, not {args.sha}. Re-read it before approving.")
    tty.write(f"Approve the plan for {key}: {_rel(root, plan)}\n  sha256 {sha}\n"
              f"Type the first 8 characters of the sha256 to approve: ")
    tty.flush()
    if tty.readline().strip().lower() != sha[:8]:
        sys.exit("Not approved.")
    rec = write_approval(root, key, plan, _who(root), "tty")
    print(f"Approved {key} (plan {sha[:12]}) by {rec['approver']}.")
    return 0


def _gh(args, root, repo):
    return st.run_gh(args, root, repo)


def reverify_github(root, key, plan, approval):
    """Called by the gate engine (which holds the signing key) for an unsigned GitHub
    approval recorded by an agent: re-check GitHub and, if it holds, sign the record."""
    pr = approval.get("pr_number")
    if not pr:
        return False
    policy = st.load_policy(root)
    ap = policy.get("approval", {})
    if ap.get("mode") != "github" or not ap.get("github_repo") or not ap.get("github_allowed_approvers"):
        return False  # only a pinned repository and a named approver list can make a GitHub approval trustworthy
    try:
        _approve_github(root, policy, key, plan, st.sha256_file(plan), pr)
    except SystemExit:
        return False
    return True


def _approve_github(root, policy, key, plan, sha, pr):
    allowed = [a.lower() for a in policy.get("approval", {}).get("github_allowed_approvers", [])]
    if policy.get("approval", {}).get("mode") == "github" and not allowed:
        sys.exit("GitHub approval mode needs approval.github_allowed_approvers in the org policy; refusing to accept "
                 "an approval from an arbitrary account.")
    # Only the pinned repository: never whatever `gh repo view` resolves from agent-writable remotes.
    repo = policy.get("approval", {}).get("github_repo") or ""
    if not repo:
        sys.exit("GitHub approval needs approval.github_repo in the policy; refusing to let gh pick the repository.")
    try:
        data = json.loads(_gh(["pr", "view", str(pr), "--json", "number,author,headRefName,headRefOid,reviews,comments,url"],
                              root, repo))
    except (RuntimeError, ValueError, OSError) as e:
        sys.exit(f"Could not read PR {pr} in {repo} with gh: {e}")
    if key not in data.get("headRefName", ""):
        sys.exit(f"PR {pr} branch '{data.get('headRefName')}' does not carry {key}.")
    rel = _rel(root, plan)
    try:
        blob = json.loads(_gh(["api", f"repos/{repo}/contents/{rel}?ref={data['headRefOid']}"], root, repo))
        remote_sha = __import__("hashlib").sha256(base64.b64decode(blob["content"])).hexdigest()
    except (RuntimeError, ValueError, KeyError, OSError) as e:
        sys.exit(f"Could not read {rel} at the PR head: {e}")
    if remote_sha != sha:
        sys.exit(f"The plan in PR {pr} ({remote_sha[:12]}) differs from the local plan ({sha[:12]}). Push the plan first.")
    who = None
    author = ((data.get("author") or {}).get("login") or "").lower()

    def eligible(login):
        # The approver must be someone other than whoever opened the PR: with a
        # locally-authenticated gh, the agent acts as the PR author, so a review
        # from that same account proves nothing about a second human.
        return login and login.lower() != author and (not allowed or login.lower() in allowed)

    for r in data.get("reviews", []):
        login = (r.get("author") or {}).get("login", "")
        if r.get("state") == "APPROVED" and eligible(login):
            who = login
    for c in data.get("comments", []):
        login = (c.get("author") or {}).get("login", "")
        if re.search(r"/approve-plan\s+" + re.escape(sha[:12]), c.get("body", "")) and eligible(login):
            who = login
    if not who:
        sys.exit(f"No approving review or `/approve-plan {sha[:12]}` comment on PR {pr}"
                 + (f" from an allowed approver ({', '.join(allowed)})." if allowed else "."))
    write_approval(root, key, plan, who, "github", {"pr": data.get("url"), "pr_number": int(pr), "head": data.get("headRefOid")})
    print(f"Recorded GitHub approval of {key} by {who} (plan {sha[:12]}).")
    return 0


def _ps_probe(pid):
    """`ppid command` of one process, or None. Runs without the key or GIT_* (REQ-IMH-22)."""
    try:
        return subprocess.run(["ps", "-o", "ppid=,command=", "-p", pid], env=st._child_env(), capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None


def _nested_claude():
    """True if the Claude Code process running this hook has another Claude Code
    process among its ancestors -- i.e. an agent launched this session from its own
    shell (e.g. `claude -p "/evidence-sdlc:approve …"`, even under a fake TTY)."""
    pid = os.environ.get("CLAUDE_PID")
    if not pid or not pid.isdigit() or os.name == "nt":
        return False
    seen = 0
    cur = pid
    while cur and cur not in ("0", "1") and seen < 64:
        seen += 1
        out = _ps_probe(cur)
        if out is None:
            return False
        if not out:
            return False
        ppid, _, cmd = out.partition(" ")
        ppid = ppid.strip()
        if cur != pid:
            exe = os.path.basename(cmd.split()[0]) if cmd.split() else ""
            if exe == "claude" or "/claude/versions/" in cmd or "claude-code/cli" in cmd or "@anthropic-ai/claude-code" in cmd:
                return True
        cur = ppid
    return False


def approve_from_prompt(root, prompt):
    """Called by the UserPromptSubmit hook: the human typed `evidence approve KEY SHA`."""
    m = re.match(r"^\s*/?evidence(?:-sdlc)?[: ]approve\s+(\S+)(?:\s+([0-9a-fA-F]{8,64}))?\s*$", prompt or "")
    if not m:
        return None
    policy = st.load_policy(root)
    if _nested_claude():
        return ("Approval not recorded: this Claude Code session was started from inside another Claude Code "
                "session, so its prompt did not come from a person. A human approves in their own session.")
    if os.environ.get("CLAUDE_CODE_SESSION_ATTENDED") == "0" and not policy.get("approval", {}).get("allow_unattended_prompt_approval"):
        return ("Approval not recorded: this is an unattended (headless) session. Approve from an interactive "
                "session, the terminal, or GitHub; or have the org policy set approval.allow_unattended_prompt_approval "
                "for a reviewed CI workflow.")
    if policy.get("approval", {}).get("mode") == "github":
        return ("Approval not recorded: this organisation's policy requires plan approval on GitHub (an approving "
                f"review or `/approve-plan <sha>` comment by an allowed approver), recorded with "
                f"`evidence approve {m.group(1)} --github-pr <N>`.")
    key, given = m.group(1), (m.group(2) or "").lower()
    state = st.load_state(root, key)
    if not state:
        return f"Approval not recorded: no change state for {key}."
    plan = st.find_artifact(root, key, "plan", state)
    s = status_dict(root, policy, key)
    if not plan or s["missing_artifacts"] or s["plan_problems"]:
        return f"Approval not recorded for {key}: " + "; ".join(s["missing_artifacts"] + s["plan_problems"] or ["no plan"])
    sha = st.sha256_file(plan)
    if not given:
        return (f"Approval not recorded: to approve, send `evidence approve {key} {sha[:12]}` — the hash pins the exact "
                f"plan version you reviewed ({_rel(root, plan)}).")
    if not sha.startswith(given):
        return (f"Approval not recorded: the plan for {key} is now {sha[:12]}, not {given}. It changed since you "
                "looked at it; re-read it before approving.")
    rec = write_approval(root, key, plan, _who(root), "prompt")
    return (f"The human approved the plan for {key} ({_rel(root, plan)}, sha256 {sha[:12]}) as {rec['approver']}. "
            "The approval is recorded in .evidence/changes/%s/approval.json and binds to this exact plan text; "
            "editing the plan voids it." % key)


def cmd_audit(args):
    root, _ = _ctx()
    d = st.audit_dir(root)
    paths = [args.path] if args.path else [os.path.join(d, n) for n in sorted(os.listdir(d))] if os.path.isdir(d) else []
    bad = 0
    for p in paths:
        if not p.endswith(".jsonl"):
            continue
        warnings = []
        ok, problems = st.audit_verify(p, warnings)
        print(f"{'OK  ' if ok else 'FAIL'} {_rel(root, p)}" + ("" if ok else ": " + "; ".join(problems[:5])))
        for w in warnings[:5]:
            print(f"     note: {w}")
        bad += 0 if ok else 1
    if not paths:
        print("No audit logs found.")
        return 1 if getattr(args, "require", False) else 0
    return 1 if bad else 0


def cmd_metrics(args):
    root, policy = _ctx()
    cdir = os.path.join(root, ".evidence", "changes")
    changes = sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []
    skipped, total_impl, by_stage = 0, 0, {}
    for k in changes:
        s = status_dict(root, policy, k)
        if not s.get("exists"):
            continue
        by_stage[s["stage"]] = by_stage.get(s["stage"], 0) + 1
        if s["stage"] in ("implementing", "failing-test", "verified", "released"):
            total_impl += 1
            if s["missing_artifacts"] or s["approval"] != "valid" or (s["stage"] in ("verified", "released") and s["missing_agents"]):
                skipped += 1
    denials, self_approval, sessions = {}, 0, set()
    for e in st.audit_events(root):
        sessions.add(e.get("session"))
        if e.get("event") == "deny":
            denials[e.get("rule")] = denials.get(e.get("rule"), 0) + 1
            if e.get("rule") == "self-approval":
                self_approval += 1
    m = {"changes": len(changes), "by_stage": by_stage,
         "stage_skip_rate": round(skipped / total_impl, 3) if total_impl else 0.0,
         "changes_past_approval": total_impl, "gate_denials": denials, "self_approval_attempts": self_approval,
         "agent_sessions_logged": len([s for s in sessions if s])}
    if args.json:
        print(json.dumps(m, indent=2, sort_keys=True))
    else:
        print(f"changes: {m['changes']}  by stage: {by_stage}")
        print(f"stage-skip rate (past approval with missing artifacts/approval/reviews): {m['stage_skip_rate']:.1%} of {total_impl}")
        print(f"gate denials: {denials or 'none'}")
        print(f"self-approval attempts: {self_approval}")
        print(f"agent sessions in audit log: {m['agent_sessions_logged']}")
    return 0


# ------------------------------------------------------------------ verify-range (ADR-0004)
# Runs in the base branch's pull_request_target workflow: the trusted CLI reads the PR's objects
# with git plumbing and executes nothing from them. Policy, CODEOWNERS and allow-lists come from
# the base commit; approval comes from a GitHub code-owner review on the head SHA.

_SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")
_RECORD = re.compile(r"^\.evidence/(?:changes/([^/]+)/(state|approval|violations)\.json|violations/([^/]+)\.json)$")
_AGENT_TRAILER = re.compile(r"^Agent-Session:\s*(\S+)\s*$", re.M)
_HUMAN_TRAILER = re.compile(r"^Human-Commit:\s*(\S+)\s*$", re.M)
_CHUNK, _OVERLAP = 1 << 20, 4096


class _Findings:
    def __init__(self):
        self.items = []

    def fail(self, rule, msg):
        if (rule, msg) not in self.items:
            self.items.append((rule, msg))


def _vg(root, args, text=True):
    return st.run_git(args, root, timeout=300, text=text)


def _blob_at(root, commit, path, text=True):
    return _vg(root, ["cat-file", "blob", f"{commit}:{path}"], text=text)


def _mode_at(root, commit, path):
    out = _vg(root, ["ls-tree", "-z", commit, "--", path])
    return out.split(" ", 1)[0] if out else None


def _json_at(root, commit, path):
    t = _blob_at(root, commit, path)
    if t is None:
        return None
    try:
        return json.loads(t)
    except ValueError:
        return {"_unparsable": True}


def _policy_at(root, commit):
    """Default and org policy plus the base commit's repository policy -- never the head's or the worktree's."""
    pol = st.load_policy(os.devnull)
    t = _blob_at(root, commit, ".evidence/policy.json")
    if t:
        try:
            pol = st._merge(pol, json.loads(t), tighten_only=True)
        except (ValueError, AttributeError, TypeError):
            pass
    return pol


def _name_status(out):
    """[(status, [paths])] from `--name-status -z` output."""
    parts, res, i = out.split("\0"), [], 0
    while i < len(parts):
        s = parts[i]
        if not s:
            i += 1
            continue
        n = 2 if s[0] in "RC" else 1
        res.append((s, parts[i + 1:i + 1 + n]))
        i += 1 + n
    return res


def _safe_session(s):
    return re.sub(r"[^A-Za-z0-9_-]", "_", s or "unknown")[:80] or "unknown"


def _codeowners(root, base):
    for p in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        t = _blob_at(root, base, p)
        if t is not None:
            rules = []
            for line in t.splitlines():
                line = line.split(" #", 1)[0].strip()
                if line and not line.startswith("#"):
                    pat, *owners = line.split()
                    rules.append((pat, owners))
            return rules
    return []


def _owners_of(rules, path):
    got = None
    for pat, owners in rules:  # the last matching rule wins
        if st.glob_to_regex(pat).match(path):
            got = owners
    return got


def _commit_list(root, base, head):
    out = _vg(root, ["rev-list", "--reverse", "--topo-order", "--parents", f"{base}..{head}"])
    return None if out is None else [l.split() for l in out.splitlines() if l.strip()]


def _is_ancestor(root, a, b):
    return _vg(root, ["merge-base", "--is-ancestor", a, b]) is not None


def _stage_index(rec):
    s = (rec or {}).get("stage")
    return st.STAGES.index(s) if s in st.STAGES else None


def _vkey(v):
    return (v.get("path"), v.get("rule"), v.get("at"), v.get("session"))


def _violation_entries(rec):
    if isinstance(rec, dict) and isinstance(rec.get("entries"), list):
        return rec["entries"]
    return rec if isinstance(rec, list) else []


def _commit_changes(root, c, parents, combined):
    if combined:
        out = _vg(root, ["diff-tree", "--cc", "-M", "--no-commit-id", "--name-status", "-z", c])
    else:
        out = _vg(root, ["diff-tree", "-r", "-M", "--root", "--no-commit-id", "--name-status", "-z", c])
    return None if out is None else _name_status(out)


def _check_paths(entries, claims, where, F):
    """Rule 2: every added, modified, deleted, type-changed or renamed path outside .evidence/ is claimed."""
    for status, paths in entries:
        for p in paths:
            if p == ".evidence" or p.startswith(".evidence/"):
                continue  # judged by rules 4-5
            if not st.claim_matches(p, claims):
                F.fail(2, f"{p} ({status[:1]} in {where}) is outside the approved plan's claims")


def _scan_blobs(root, commits, pol, base, F):
    """Rule 3: every blob a commit adds is scanned for secrets, in chunks with overlap, and size-capped."""
    import secretscan
    cap = int(pol.get("verify_range_blob_cap_mb", 20)) * 1024 * 1024
    allow_large = pol.get("verify_range_allow_large", [])
    try:
        al = json.loads(_blob_at(root, base, ".evidence/secrets-allowlist.json") or "[]")
        allowlist = [e["fingerprint"] if isinstance(e, dict) else e
                     for e in (al.get("fingerprints", []) if isinstance(al, dict) else al)]
    except (ValueError, KeyError, TypeError):
        allowlist = []
    seen = set()
    for c, *parents in commits:
        args = ["diff-tree", "-r", "--no-commit-id", "--raw", "-z"] + ([parents[0], c] if parents else ["--root", c])
        out = _vg(root, args)
        if out is None:
            F.fail(3, f"git could not list the blobs of {c[:12]}")
            continue
        parts, i = out.split("\0"), 0
        while i < len(parts):
            meta = parts[i]
            if not meta.startswith(":"):
                i += 1
                continue
            f = meta[1:].split()
            n = 2 if f[4][:1] in "RC" else 1
            path = parts[i + n] if i + n < len(parts) else ""
            i += 1 + n
            sha, mode = f[3], f[1]
            if set(sha) == {"0"} or mode == "160000" or sha in seen:
                continue
            seen.add(sha)
            size = _vg(root, ["cat-file", "-s", sha])
            if size is None:
                F.fail(3, f"git could not read the blob of {path} in {c[:12]}")
                continue
            if int(size) > cap:
                if not st.glob_match(path, allow_large):
                    F.fail(3, f"{path} in {c[:12]} is {int(size) >> 20} MiB, over the {cap >> 20} MiB cap and not on the "
                              "org allow-list (verify_range_allow_large)")
                continue
            data = _vg(root, ["cat-file", "blob", sha], text=False) or b""
            text = data.decode("utf-8", "replace")
            for start in range(0, max(len(text), 1), _CHUNK):
                for hit in secretscan.scan(text[max(0, start - _OVERLAP):start + _CHUNK], allowlist):
                    F.fail(3, f"possible secret in {path} added in {c[:12]}: {hit['rule']} (fingerprint {hit['fingerprint']})")


def _check_audit(root, base, head, commits, sessions, F):
    """Rule 4: named sessions' logs exist at the head and verify; base logs are neither deleted nor
    type-changed; every log in every commit is a byte-prefix extension of that log in each parent."""
    for s in sorted(sessions):
        name = f"{_safe_session(s)}.jsonl"
        text = _blob_at(root, head, f".evidence/audit/{name}")
        if text is None:
            F.fail(4, f"the audit log of session {s} (.evidence/audit/{name}) is missing at the head")
            continue
        ok, problems = st.audit_verify_lines(name, text.splitlines(), [])
        if not ok:
            F.fail(4, f".evidence/audit/{name} does not verify: {'; '.join(problems[:3])}")
    base_logs = (_vg(root, ["ls-tree", "-r", "--name-only", "-z", base, "--", ".evidence/audit"]) or "").split("\0")
    for p in filter(None, base_logs):
        if _mode_at(root, head, p) != _mode_at(root, base, p):
            F.fail(4, f"{p}, which exists at the base, is deleted or type-changed at the head")
    for c, *parents in commits:
        for p in parents:
            out = _vg(root, ["diff", "--name-only", "-z", p, c, "--", ".evidence/audit"])
            if out is None:
                F.fail(4, f"git could not compare the audit logs of {c[:12]} with its parent")
                continue
            for path in filter(None, out.split("\0")):
                old = _blob_at(root, p, path, text=False)
                if old is None:
                    continue  # a new log; named sessions' logs are verified above
                new = _blob_at(root, c, path, text=False)
                if new is None or _mode_at(root, c, path) != _mode_at(root, p, path) or not new.startswith(old):
                    F.fail(4, f"{path} in {c[:12]} is not an append-only extension of its parent's version "
                              "(truncated, rewritten, replaced or deleted)")


def _check_records(root, base, head, commits, key, own_branch_file, F):
    """Rule 5: change records at the head verify; none at the base is deleted or type-changed; stages
    never move backwards; violations are never rolled back or closed without a signed clear; other
    changes' records change only by a signed release or a signed clear. `key` None = push report."""
    import signing

    def mine(path):
        m = _RECORD.match(path)
        return bool(m) and key is not None and (m.group(1) == key or m.group(3) == own_branch_file)

    net = _vg(root, ["diff", "--name-only", "-z", f"{base}...{head}", "--", ".evidence"])
    if net is None:
        F.fail(5, "git could not list the change records that differ from the base")
        return
    for path in filter(None, net.split("\0")):
        m = _RECORD.match(path)
        if not m:
            continue
        rec = _json_at(root, head, path)
        if rec is None:
            if _mode_at(root, base, path):
                F.fail(5, f"{path}, which exists at the base, is deleted at the head")
            continue
        if not isinstance(rec, dict) or signing.verify(rec) is not True:
            F.fail(5, f"{path} at the head is not signed by the gate engine (or its signature is invalid)")
    base_recs = (_vg(root, ["ls-tree", "-r", "--name-only", "-z", base, "--", ".evidence"]) or "").split("\0")
    for path in filter(None, base_recs):
        if _RECORD.match(path) and _mode_at(root, head, path) != _mode_at(root, base, path):
            F.fail(5, f"{path}, which exists at the base, is deleted or type-changed at the head")
    for c, *parents in commits:
        for p in parents:
            out = _vg(root, ["diff", "--name-only", "-z", p, c, "--", ".evidence"])
            for path in filter(None, (out or "").split("\0")):
                m = _RECORD.match(path)
                if not m:
                    continue
                old, new = _json_at(root, p, path), _json_at(root, c, path)
                if new is None:
                    if old is not None:
                        F.fail(5, f"{path} is deleted in {c[:12]}")
                    continue
                kind = m.group(2) or "violations"
                if kind == "state" and old is not None:
                    a, b = _stage_index(old), _stage_index(new)
                    if a is None or b is None or b < a:
                        F.fail(5, f"{path}: stage moves from {old.get('stage')} to {new.get('stage')} in {c[:12]}")
                if kind == "violations":
                    now = {_vkey(v): v for v in _violation_entries(new)}
                    for v in _violation_entries(old or {}):
                        if not v.get("open"):
                            continue
                        w = now.get(_vkey(v))
                        if w is None:
                            F.fail(5, f"{path}: open violation {v.get('path')} ({v.get('rule')}) removed in {c[:12]}")
                        elif not w.get("open") and not w.get("cleared_by"):
                            F.fail(5, f"{path}: violation {v.get('path')} ({v.get('rule')}) closed without a signed "
                                      f"clear in {c[:12]}")
                if key is None or mine(path):
                    continue
                if old is None:
                    if kind == "approval":  # a change's approval arrives with its own PR, never in another's
                        F.fail(5, f"{path} (another change's approval) is added in {c[:12]}")
                    continue
                # another change's record: only a signed release or a signed clear
                if kind == "state":
                    def rest(r):
                        return {k: v for k, v in r.items() if k not in ("stage", "history", "sig")}
                    if not (new.get("stage") == "released" and rest(new) == rest(old)):
                        F.fail(5, f"{path} (another change) is edited in {c[:12]} other than by a release")
                elif kind == "approval":
                    if new != old:
                        F.fail(5, f"{path} (another change) is edited in {c[:12]}")
                else:
                    was = {_vkey(v): v for v in _violation_entries(old)}
                    for k2, w in {_vkey(v): v for v in _violation_entries(new)}.items():
                        v = was.get(k2)
                        closed = v is not None and v.get("open") and not w.get("open") and w.get("cleared_by")
                        if v is None or (w != v and not closed):
                            F.fail(5, f"{path} (another change) is edited in {c[:12]} other than by a signed clear")


def _review_approval(root, repo, number, head, author, paths, base, F):
    """Rule 1: an APPROVED review on the head SHA, not by the PR author, from a user who owns every
    changed path by the base's CODEOWNERS (last matching rule; team owners unsupported)."""
    try:
        reviews = json.loads(st.run_gh(["api", f"repos/{repo}/pulls/{number}/reviews?per_page=100"], root, repo))
    except (RuntimeError, ValueError, OSError) as e:
        F.fail(1, f"could not read the PR's reviews: {e}")
        return
    latest = {}
    for rv in reviews if isinstance(reviews, list) else []:
        login = ((rv.get("user") or {}).get("login") or "").lower()
        if login and rv.get("state") in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            latest[login] = rv
    approvers = {l for l, rv in latest.items()
                 if rv.get("state") == "APPROVED" and rv.get("commit_id") == head and l != (author or "").lower()}
    if not approvers:
        F.fail(1, f"no approving review on the head commit {head[:12]} by someone other than the PR author")
        return
    rules = _codeowners(root, base)
    for p in sorted(set(paths)):
        owners = _owners_of(rules, p)
        if not owners:
            F.fail(1, f"{p} has no code owner in the base's CODEOWNERS, so no review can approve it")
            continue
        if any("/" in o or not o.startswith("@") for o in owners):
            F.fail(1, f"{p} is owned by {' '.join(owners)}: team and e-mail owners are not supported by verify-range")
            continue
        if not approvers & {o[1:].lower() for o in owners}:
            F.fail(1, f"{p} is owned by {' '.join(owners)}, and none of them approved the head commit")


def _verify_pr(root, F):
    import signing
    # rule 0: inputs, fail closed
    name = os.environ.get("GITHUB_EVENT_NAME", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    try:
        with open(os.environ.get("GITHUB_EVENT_PATH", "")) as f:
            ev = json.load(f)
    except (OSError, ValueError) as e:
        F.fail(0, f"the event payload ($GITHUB_EVENT_PATH) could not be read ({e})")
        return
    if len(os.environ.get(signing.ENV, "")) < 32 or not signing.enabled():
        F.fail(0, "no signing key of at least 32 characters, so records cannot be verified")
    if not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        F.fail(0, "no GitHub token (GH_TOKEN or GITHUB_TOKEN), so reviews cannot be read")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        F.fail(0, "GITHUB_REPOSITORY is not set to owner/name")
    if F.items:
        return
    if name == "pull_request_target":
        pr = ev.get("pull_request") or {}
    elif name == "workflow_dispatch":
        n = str((ev.get("inputs") or {}).get("pr", ""))
        if not n.isdigit():
            F.fail(0, "workflow_dispatch needs the PR number as input `pr`")
            return
        try:
            pr = json.loads(st.run_gh(["api", f"repos/{repo}/pulls/{n}"], root, repo))
        except (RuntimeError, ValueError, OSError) as e:
            F.fail(0, f"could not read PR {n}: {e}")
            return
    else:
        F.fail(0, f"event {name or '(none)'} is not pull_request_target or workflow_dispatch (use --push-report for push)")
        return
    number = pr.get("number")
    base = str((pr.get("base") or {}).get("sha") or "")
    head = str((pr.get("head") or {}).get("sha") or "")
    ref = str((pr.get("head") or {}).get("ref") or "")
    author = str((pr.get("user") or {}).get("login") or "")
    if not isinstance(number, int) or not _SHA.fullmatch(base) or not _SHA.fullmatch(head):
        F.fail(0, "the PR number, base SHA or head SHA is missing or malformed")
        return
    fetched = (_vg(root, ["rev-parse", "--verify", "-q", f"refs/pull/{number}/head^{{commit}}"]) or "").strip()
    if fetched != head:
        F.fail(0, f"refs/pull/{number}/head ({fetched[:12] or 'missing'}) is not the event's head {head[:12]}")
    if _vg(root, ["rev-parse", "--verify", "-q", f"{base}^{{commit}}"]) is None:
        F.fail(0, f"the base commit {base[:12]} is not available")
    if F.items:
        return
    pol = _policy_at(root, base)
    commits = _commit_list(root, base, head)
    if commits is None:
        F.fail(0, "git could not list the commits in the range")
        return

    # rule 1: the change and its approval
    keys = list(dict.fromkeys(st.find_keys(ref, pol)))
    key = keys[0] if len(keys) == 1 else None
    if key is None:
        F.fail(1, f"the head branch {ref!r} must carry exactly one change key (found {len(keys)})")
    claims, sessions, checked = None, set(), []
    for c, *parents in commits:
        combined = len(parents) > 1
        changes = _commit_changes(root, c, parents, combined)
        if changes is None:
            F.fail(2, f"git could not list the paths of {c[:12]}")
            continue
        if combined and not changes and all(_is_ancestor(root, p, base) for p in parents[1:]):
            continue  # a clean "Update branch" merge of the base
        checked.append((c, changes))
        msg = _vg(root, ["log", "-1", "--format=%B", c]) or ""
        if key and key not in st.find_keys(msg, pol):
            F.fail(1, f"commit {c[:12]} does not carry the change key {key}")
        agent, human = _AGENT_TRAILER.findall(msg), _HUMAN_TRAILER.findall(msg)
        if not agent and not human:
            F.fail(1, f"commit {c[:12]} has neither an Agent-Session: nor a Human-Commit: trailer")
        sessions.update(agent)
    if key:
        state_head = _json_at(root, head, f".evidence/changes/{key}/state.json")
        state_base = _json_at(root, base, f".evidence/changes/{key}/state.json")
        if not isinstance(state_head, dict) or signing.verify(state_head) is not True:
            F.fail(1, f"the state of {key} at the head is missing or not signed by the gate engine")
        elif state_head.get("stage") == "released":
            F.fail(1, f"{key} is already released at the head")
        if isinstance(state_base, dict) and state_base.get("stage") == "released":
            F.fail(1, f"{key} was released at the base: a released change key cannot be reused")
        appr = _json_at(root, head, f".evidence/changes/{key}/approval.json")
        if not isinstance(appr, dict) or signing.verify(appr) is not True:
            F.fail(1, f"the approval record of {key} at the head is missing or not signed")
        else:
            plan = _blob_at(root, head, str(appr.get("plan_path") or ""), text=False)
            if plan is None or __import__("hashlib").sha256(plan).hexdigest() != appr.get("plan_sha256"):
                F.fail(1, f"the plan at {appr.get('plan_path')} does not match the approved hash in approval.json")
            else:
                claims = st.plan_claims(plan.decode("utf-8", "replace"))
    net = _vg(root, ["diff", "-M", "--name-status", "-z", f"{base}...{head}"])
    net_changes = _name_status(net) if net is not None else None
    if net_changes is None:
        F.fail(2, "git could not compute the net diff base...head")
        net_changes = []
    _review_approval(root, repo, number, head, author, [p for _, ps in net_changes for p in ps], base, F)

    # rule 2: paths
    if claims is not None:
        for c, changes in checked:
            _check_paths(changes, claims, c[:12], F)
        _check_paths(net_changes, claims, "the net diff", F)
    # rules 3-5
    _scan_blobs(root, commits, pol, base, F)
    _check_audit(root, base, head, commits, sessions, F)
    _check_records(root, base, head, commits, key, _safe_branch(ref), F)


def _safe_branch(ref):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", ref or "detached")


def _verify_push(root, F):
    """Rule 7: after a push to main, report rules 2-5 over before..after. Never blocks."""
    try:
        with open(os.environ.get("GITHUB_EVENT_PATH", "")) as f:
            ev = json.load(f)
    except (OSError, ValueError) as e:
        F.fail(0, f"the event payload could not be read ({e})")
        return
    before, after = str(ev.get("before") or ""), str(ev.get("after") or "")
    if before and set(before) == {"0"}:
        print("verify-range: skipped: first push to this branch (all-zero `before`), nothing to compare.")
        return
    if not _SHA.fullmatch(before) or not _SHA.fullmatch(after):
        F.fail(0, "the push event's before/after SHAs are missing or malformed")
        return
    pol = _policy_at(root, before)
    commits = _commit_list(root, before, after)
    if commits is None:
        F.fail(0, "git could not list the pushed commits")
        return
    sessions = set()
    for c, *parents in commits:
        combined = len(parents) > 1
        changes = _commit_changes(root, c, parents, combined) or []
        msg = _vg(root, ["log", "-1", "--format=%B", c]) or ""
        sessions.update(_AGENT_TRAILER.findall(msg))
        keys = list(dict.fromkeys(st.find_keys(msg, pol)))
        appr = _json_at(root, c, f".evidence/changes/{keys[0]}/approval.json") if len(keys) == 1 else None
        plan = _blob_at(root, c, str(appr.get("plan_path") or "")) if isinstance(appr, dict) else None
        if plan is None:
            if changes and not (combined and all(_is_ancestor(root, p, before) for p in parents[1:])):
                F.fail(2, f"{c[:12]} has no single change key with an approved plan, so its paths are unchecked: "
                          + ", ".join(p for _, ps in changes for p in ps)[:300])
            continue
        _check_paths(changes, st.plan_claims(plan), c[:12], F)
    _scan_blobs(root, commits, pol, before, F)
    _check_audit(root, before, after, commits, sessions, F)
    _check_records(root, before, after, commits, None, None, F)


def cmd_verify_range(args):
    root = st.repo_root(os.getcwd())
    F = _Findings()
    try:
        (_verify_push if args.push_report else _verify_pr)(root, F)
    except Exception as e:  # never a traceback, never a pass
        F.fail(0, f"verify-range could not complete ({type(e).__name__}: {e})")
    for rule, msg in F.items:
        print(f"FAIL rule {rule}: {msg}")
    if args.push_report:
        print(f"verify-range (push report): {len(F.items)} finding(s). This report never blocks.")
        return 0
    if F.items:
        print(f"verify-range: {len(F.items)} failure(s). See ADR-0004 for the rules.")
        return 1
    print("verify-range: OK.")
    return 0


def register(sub):
    p = sub.add_parser("change", help="start, inspect and advance a change's lifecycle state")
    csub = p.add_subparsers(dest="change_cmd", required=True)
    s = csub.add_parser("start")
    s.add_argument("key")
    s.add_argument("--tier", required=True, choices=["1", "2", "3"])
    s.add_argument("--kind", default="feature", choices=["feature", "fix", "chore"])
    s.add_argument("--plan")
    s.add_argument("--spec")
    s.add_argument("--intent")
    s.add_argument("--quick", metavar="SUMMARY", help="Tier 1 fast path: generate a minimal plan from --files")
    s.add_argument("--files", nargs="+", default=[])
    for name in ("status",):
        x = csub.add_parser(name)
        x.add_argument("key", nargs="?")
        x.add_argument("--json", action="store_true")
    x = csub.add_parser("list")
    x.add_argument("--json", action="store_true")
    x = csub.add_parser("advance")
    x.add_argument("key")
    x.add_argument("stage")
    x = csub.add_parser("set-tier")
    x.add_argument("key")
    x.add_argument("tier", choices=["1", "2", "3"])
    x = csub.add_parser("release")
    x.add_argument("key")
    x = csub.add_parser("clear-violations")
    x.add_argument("key")
    p.set_defaults(func=cmd_change)

    a = sub.add_parser("approve", help="human approval of a change's plan (terminal, prompt or GitHub)")
    a.add_argument("key", nargs="?")
    a.add_argument("sha", nargs="?")
    a.add_argument("--github-pr", type=int)
    a.set_defaults(func=cmd_approve)

    au = sub.add_parser("audit", help="verify the hash-chained audit logs")
    ausub = au.add_subparsers(dest="audit_cmd", required=True)
    v = ausub.add_parser("verify")
    v.add_argument("path", nargs="?")
    v.add_argument("--require", action="store_true", help="fail when no audit logs exist")
    au.set_defaults(func=cmd_audit)

    m = sub.add_parser("metrics", help="stage-skip rate, gate denials, self-approval attempts")
    m.add_argument("--json", action="store_true")
    m.set_defaults(func=cmd_metrics)

    vr = sub.add_parser("verify-range", help="CI: check a PR's commits against ADR-0004 (reads $GITHUB_EVENT_PATH)")
    vr.add_argument("--push-report", action="store_true", help="after a push to main: report rules 2-5, never block")
    vr.set_defaults(func=cmd_verify_range)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="evidence")
    sub = ap.add_subparsers(dest="cmd", required=True)
    register(sub)
    args = ap.parse_args(argv)
    return args.func(args)
