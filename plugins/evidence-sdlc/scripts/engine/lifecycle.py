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


def _human_tty():
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        raise HumanOnly("this runs inside a Claude Code session")
    try:
        return open("/dev/tty", "r+")
    except OSError:
        raise HumanOnly("there is no terminal to confirm on")


def _who(root):
    email = st.git(["config", "user.email"], root)
    return (email or "").strip() or os.environ.get("USER") or getpass.getuser()


def _ctx():
    root = st.repo_root(os.getcwd())
    return root, st.load_policy(root)


def _key_arg(args, root, policy):
    if getattr(args, "key", None):
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
        first = {3: "intent", 2: "spec", 1: "plan"}[tier]
        state = {"key": key, "tier": tier, "kind": args.kind, "stage": first, "created_at": st.now(),
                 "created_by": _who(root), "history": [{"stage": first, "at": st.now(), "by": _who(root)}]}
        for a in ("intent", "spec", "plan"):
            v = getattr(args, a, None)
            if v:
                state[a] = v
        if getattr(args, "quick", None):
            if tier != 1 or not args.files:
                sys.exit("--quick is for Tier 1 changes and needs --files <glob> [...]")
            plan_rel = state.get("plan") or f"plan/{key}.md"
            os.makedirs(os.path.join(root, os.path.dirname(plan_rel)), exist_ok=True)
            with open(os.path.join(root, plan_rel), "w") as f:
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
        state.setdefault("history", []).append({"stage": target, "at": st.now(), "by": _who(root)})
        st.save_state(root, key, state)
        print(f"{key} -> {target}")
        return 0
    if sub in ("set-tier", "release", "override"):
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
            st.write_violations(p, data)
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
    d = st.change_dir(root, key)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "approval.json"), "w") as f:
        json.dump(rec, f, indent=2, sort_keys=True)
        f.write("\n")
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


def _gh(args):
    exe = os.environ.get("EVIDENCE_GH", "gh")
    r = subprocess.run([exe] + args, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"gh {' '.join(args)} failed")
    return r.stdout


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
    try:
        data = json.loads(_gh(["pr", "view", str(pr), "--json", "number,author,headRefName,headRefOid,reviews,comments,url"]))
    except (RuntimeError, ValueError, OSError) as e:
        sys.exit(f"Could not read PR {pr} with gh: {e}")
    if key not in data.get("headRefName", ""):
        sys.exit(f"PR {pr} branch '{data.get('headRefName')}' does not carry {key}.")
    rel = _rel(root, plan)
    try:
        repo = policy.get("approval", {}).get("github_repo") or json.loads(_gh(["repo", "view", "--json", "nameWithOwner"]))["nameWithOwner"]
        if policy.get("approval", {}).get("github_repo"):
            data_repo = json.loads(_gh(["pr", "view", str(pr), "--repo", repo, "--json", "number"]))  # must exist in the pinned repo
            if not data_repo:
                sys.exit(f"PR {pr} not found in {repo}")
        blob = json.loads(_gh(["api", f"repos/{repo}/contents/{rel}?ref={data['headRefOid']}"]))
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
        try:
            out = subprocess.run(["ps", "-o", "ppid=,command=", "-p", cur], capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
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
        ok, problems = st.audit_verify(p)
        print(f"{'OK  ' if ok else 'FAIL'} {_rel(root, p)}" + ("" if ok else ": " + "; ".join(problems[:5])))
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


def main(argv=None):
    ap = argparse.ArgumentParser(prog="evidence")
    sub = ap.add_subparsers(dest="cmd", required=True)
    register(sub)
    args = ap.parse_args(argv)
    return args.func(args)
