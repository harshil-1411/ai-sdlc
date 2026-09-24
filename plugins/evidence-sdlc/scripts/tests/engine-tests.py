#!/usr/bin/env python3
"""Regression suite for the v2 gate engine (PILOT-53).

Every probe from the v1 enterprise audit's security table is a case here, run
exactly as Claude Code runs the hook: a JSON payload on stdin to hook.py, in a
throwaway git repository. Cases are grouped by requirement ID. Run:

    python3 plugins/evidence-sdlc/scripts/tests/engine-tests.py [-v] [-k substring]
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(HERE, "..", "engine", "hook.py")
VERBOSE = "-v" in sys.argv
FILTER = sys.argv[sys.argv.index("-k") + 1] if "-k" in sys.argv else None

results = {"pass": 0, "fail": 0, "failures": [], "all": []}
BASE_ENV = {k: v for k, v in os.environ.items()
            if k not in ("EVIDENCE_ISSUE_KEY_PATTERN", "CHANGE_TICKET", "RELEASE_APPROVAL",
                         "EVIDENCE_ACTIVE_CHANGE", "EVIDENCE_ORG_POLICY", "FIX_TASK")}
BASE_ENV["GIT_AUTHOR_NAME"] = BASE_ENV["GIT_COMMITTER_NAME"] = "test"
BASE_ENV["GIT_AUTHOR_EMAIL"] = BASE_ENV["GIT_COMMITTER_EMAIL"] = "test@example.com"
BASE_ENV["EVIDENCE_ORG_POLICY"] = "/nonexistent/org-policy.json"

PLAN_TEMPLATE = """# Plan: test change
Tracker: {key}   From: spec.md   Date: 2026-09-24
Risk tier: {tier}

## Files claimed
{claims}

## Files that change
- as claimed

## Order of work
1. Make the change described in the spec, with tests, and nothing else.
2. Run the suite.

## Proof
| REQ ID | Layer | Automated? | Test case ID | Automated test | Evidence |
| --- | --- | --- | --- | --- | --- |
| REQ-T-01 | unit | Yes | — | tests/test_app.py | test output |
"""


def sh(cmd, cwd, env=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, env=env or BASE_ENV)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd}: {r.stderr}")
    return r.stdout


def run_hook(repo, payload, event="pre", env_extra=None, raw=None):
    env = dict(BASE_ENV)
    env.update(env_extra or {})
    data = raw if raw is not None else json.dumps(payload)
    r = subprocess.run([sys.executable, HOOK, event], input=data, cwd=repo, capture_output=True, text=True, env=env)
    out = r.stdout.strip()
    try:
        obj = json.loads(out) if out else {}
    except ValueError:
        obj = {"_raw": out}
    return obj, r.stderr


def decision(obj):
    hso = obj.get("hookSpecificOutput", {})
    return ("deny" if hso.get("permissionDecision") == "deny" else "allow"), hso.get("permissionDecisionReason", "")


def case(label, repo, tool, tool_input, expect, env=None, perm="default", agent_type=None, session="s1",
         raw=None, rule_hint=None):
    if FILTER and FILTER not in label:
        return
    payload = {"session_id": session, "cwd": repo, "hook_event_name": "PreToolUse", "tool_name": tool,
               "tool_input": tool_input, "permission_mode": perm}
    if agent_type:
        payload["agent_type"] = agent_type
        payload["agent_id"] = "a1"
    obj, err = run_hook(repo, payload, env_extra=env, raw=raw)
    got, reason = decision(obj)
    ok = got == expect and (rule_hint is None or rule_hint.lower() in reason.lower())
    results["all"].append((label, ok, "" if ok else f"expected {expect}, got {got}: {reason[:300]}"))
    if ok:
        results["pass"] += 1
        if VERBOSE:
            print(f"PASS {label}")
    else:
        results["fail"] += 1
        results["failures"].append(label)
        print(f"FAIL {label}: expected {expect}{' (' + rule_hint + ')' if rule_hint else ''}, got {got}: {reason[:300]} {err[-400:]}")


def check(label, ok, detail=""):
    """Ad-hoc assertion with a REQ-labelled title (structural tag for `evidence gaps`)."""
    if FILTER and FILTER not in label:
        return
    results["pass" if ok else "fail"] += 1
    results["all"].append((label, bool(ok), "" if ok else str(detail)[:500]))
    if not ok:
        results["failures"].append(label)
        print(f"FAIL {label}: {detail}")
    elif VERBOSE:
        print(f"PASS {label}")


def write_junit(path, suite):
    from xml.sax.saxutils import escape, quoteattr
    fails = sum(1 for _, ok, _ in results["all"] if not ok)
    with open(path, "w") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name={quoteattr(suite)} '
                f'tests="{len(results["all"])}" failures="{fails}">\n')
        for label, ok, detail in results["all"]:
            f.write(f'  <testcase classname={quoteattr(suite)} name={quoteattr(label)}>')
            if not ok:
                f.write(f'<failure message={quoteattr(detail[:200])}>{escape(detail)}</failure>')
            f.write("</testcase>\n")
        f.write("</testsuite>\n")


def edit(p):
    return ("Edit", {"file_path": p, "old_string": "a", "new_string": "b"})


def write(p, content="x = 1\n"):
    return ("Write", {"file_path": p, "content": content})


def bash(c):
    return ("Bash", {"command": c})


# ------------------------------------------------------------------ fixtures

def make_repo(branch="feature/ABC-1-login"):
    d = os.path.realpath(tempfile.mkdtemp(prefix="evidence-engine-"))
    sh("git init -q -b main", d)
    os.makedirs(os.path.join(d, "src", "auth"))
    os.makedirs(os.path.join(d, "tests"))
    os.makedirs(os.path.join(d, "spec", "models"))
    os.makedirs(os.path.join(d, "docs"))
    os.makedirs(os.path.join(d, "db", "migrations"))
    for p, c in {"src/app.py": "a = 1\n", "src/auth/login.py": "a = 1\n", "tests/test_app.py": "a = 1\n",
                 "spec/models/user_spec.rb": "a = 1\n", "docs/guide.md": "a\n", "README.md": "a\n",
                 "db/migrations/001.sql": "a\n"}.items():
        with open(os.path.join(d, p), "w") as f:
            f.write(c)
    sh("git add -A && git commit -q -m 'ABC-0: init'", d)
    sh(f"git checkout -q -b {branch}", d)
    return d


def start_change(repo, key="ABC-1", tier=1, kind="feature", claims=("src/app.py", "tests/**"), approve=True,
                 fix_base=None, stage="approved"):
    cdir = os.path.join(repo, ".evidence", "changes", key)
    os.makedirs(cdir, exist_ok=True)
    plan_rel = f"plan/{key}.md"
    os.makedirs(os.path.join(repo, "plan"), exist_ok=True)
    plan_text = PLAN_TEMPLATE.format(key=key, tier=tier, claims="\n".join(f"- `{c}`" for c in claims))
    with open(os.path.join(repo, plan_rel), "w") as f:
        f.write(plan_text)
    state = {"key": key, "tier": tier, "kind": kind, "stage": stage, "plan": plan_rel}
    if tier >= 2:
        spec = f"intent/{key}/spec.md"
        os.makedirs(os.path.join(repo, "intent", key), exist_ok=True)
        with open(os.path.join(repo, spec), "w") as f:
            f.write(f"# Spec\nTracker: {key}\nRisk tier: {tier}\n")
        state["spec"] = spec
    if tier >= 3:
        intent = f"intent/{key}/intent.md"
        with open(os.path.join(repo, intent), "w") as f:
            f.write(f"# Intent\nTracker: {key}\n")
        state["intent"] = intent
    if fix_base:
        state["fix_base"] = fix_base
    with open(os.path.join(cdir, "state.json"), "w") as f:
        json.dump(state, f)
    ap = os.path.join(cdir, "approval.json")
    if approve:
        sha = hashlib.sha256(open(os.path.join(repo, plan_rel), "rb").read()).hexdigest()
        with open(ap, "w") as f:
            json.dump({"key": key, "plan_path": plan_rel, "plan_sha256": sha, "approver": "human",
                       "method": "tty", "approved_at": "2026-09-24T00:00:00Z"}, f)
    elif os.path.exists(ap):
        os.remove(ap)
    return os.path.join(repo, plan_rel)


def record_agent(repo, key, agent):
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import state as st
    st.audit_append(repo, "s1", {"event": "agent-completed", "key": key, "subagent_type": agent, "tool": "Agent"})


# ------------------------------------------------------------------ suites

def suite_fail_closed():
    r = make_repo()
    case("REQ-V2G-01 malformed JSON denies", r, "Edit", {}, "deny", raw="not json", rule_hint="failing closed")
    case("REQ-V2G-01 empty input denies", r, "Edit", {}, "deny", raw="", rule_hint="failing closed")
    case("REQ-V2G-01 Edit without path denies", r, "Edit", {"old_string": "a"}, "deny")
    case("REQ-V2G-01 Bash without command denies", r, "Bash", {}, "deny")
    env = dict(BASE_ENV)
    env["PATH"] = "/nonexistent"
    rr = subprocess.run(["/bin/bash", os.path.join(HERE, "..", "engine", "hook.sh"), "pre"],
                        input=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "src/app.py"}}),
                        capture_output=True, text=True, env=env, cwd=r)
    ok = '"permissionDecision":"deny"' in rr.stdout.replace(" ", "")
    results["pass" if ok else "fail"] += 1
    if not ok:
        results["failures"].append("REQ-V2G-01 missing python3 denies")
        print("FAIL REQ-V2G-01 missing python3 denies:", rr.stdout, rr.stderr)
    shutil.rmtree(r)


def suite_no_change():
    r = make_repo(branch="feature/x")
    # A stale plan from another change, an empty plan, and a node_modules plan must not unlock anything.
    os.makedirs(os.path.join(r, "intent", "2020-01-01-stale"))
    open(os.path.join(r, "intent", "2020-01-01-stale", "plan.md"), "w").write("")
    os.makedirs(os.path.join(r, "node_modules", "x"))
    open(os.path.join(r, "node_modules", "plan.md"), "w").write("# plan\n")
    open(os.path.join(r, "plan.md"), "w").write("# Plan\nTracker: OLD-9\n## Files claimed\n- `src/**`\n## Order of work\n1. x\n" + "x" * 300)
    t, i = edit("src/app.py")
    case("REQ-V2G-04 no key in branch denies source edit despite stale plans", r, t, i, "deny", rule_hint="needs an active change")
    t, i = edit(os.path.join(r, "src", "app.py"))
    case("REQ-V2G-03 absolute path under a tmp directory is gated", r, t, i, "deny")
    t, i = edit("src/docs/../app.py")
    case("REQ-V2G-03 traversal through an exempt-looking segment is gated", r, t, i, "deny")
    t, i = edit("docs/guide.md")
    case("REQ-V2G-03 markdown docs stay ungated", r, t, i, "allow")
    t, i = edit("README.md")
    case("REQ-V2G-03 README stays ungated", r, t, i, "allow")
    for p in (".github/workflows/ci.yml", "package.json", "config/app.yaml"):
        t, i = write(p)
        case(f"REQ-V2G-03 {p} is no longer blanket-exempt", r, t, i, "deny")
    case("REQ-V2G-03 NotebookEdit is gated", r, "NotebookEdit", {"notebook_path": "src/a.ipynb", "new_source": "x"}, "deny")
    for c in ["cat > src/x.py <<'E'\nprint(1)\nE", "sed -i 's/a/b/' src/app.py", "sed -i.bak -e 's/a/b/' src/app.py",
              "echo x >> src/app.py", "tee src/new.py < /dev/null", "cp /etc/hosts src/hosts.py", "mv src/app.py src/app2.py",
              "rm -f src/app.py", "git checkout -- src/app.py", "truncate -s0 src/app.py", "dd if=/dev/zero of=src/app.py count=1",
              "printf 'x' | tee -a src/app.py", "cd src && echo x > app.py", "bash -c 'echo x > src/app.py'",
              "echo $(echo x > src/app.py)", "perl -pi -e 's/a/b/' src/app.py"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 Bash write denied: {c.splitlines()[0][:40]}", r, t, i, "deny")
    for c in ["python3 -c \"open('src/x.py','w').write('x')\"", "python3 - <<'EOF'\nimport pathlib\npathlib.Path('src/x.py').write_text('x')\nEOF",
              "node -e \"require('fs').writeFileSync('src/x.js','x')\"", "git apply fix.patch", "patch -p1 < fix.patch"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 opaque write denied: {c.splitlines()[0][:40]}", r, t, i, "deny", rule_hint="cannot inspect")
    for c in ["python3 -m unittest discover -s tests", "grep -rn production docs/", "git status && git log --oneline -5",
              "echo hi > /dev/null", "ls -la src 2>&1", "python3 -c \"print(1+1)\"", "cat src/app.py | wc -l",
              "git diff HEAD~1 -- src/app.py", "find . -name '*.py' | head", "grep -rn deploy src/ | grep prod",
              "echo 'remember to deploy to production later'", "npm test", "pytest -q tests"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 read-only Bash allowed: {c[:40]}", r, t, i, "allow")
    t, i = bash("echo x > /tmp/scratch-note.txt")
    case("REQ-V2G-02 writes outside the repo are not this gate's concern", r, t, i, "allow")
    shutil.rmtree(r)


def suite_control_plane():
    r = make_repo()
    start_change(r, claims=("src/**", ".claude/**", ".evidence/**"))
    for p in (".claude/settings.json", ".claude/settings.local.json", ".evidence/policy.json",
              ".evidence/changes/ABC-1/approval.json", ".evidence/changes/ABC-1/state.json",
              ".evidence/secrets-allowlist.json", ".evidence/audit/s1.jsonl", "managed-settings.json"):
        t, i = write(p, "{}")
        case(f"REQ-V2G-09 control plane write denied: {p}", r, t, i, "deny", rule_hint="control plane")
    t, i = bash("echo '{}' > .evidence/changes/ABC-1/approval.json")
    case("REQ-V2G-09 control plane Bash write denied", r, t, i, "deny", rule_hint="control plane")
    t, i = write(os.path.expanduser("~/.claude/settings.json"), "{}")
    case("REQ-V2G-09 user settings write denied", r, t, i, "deny", rule_hint="configuration")
    for c in ["evidence approve ABC-1", "python3 plugins/evidence-sdlc/bin/evidence approve ABC-1 --yes",
              "evidence change set-tier ABC-1 1", "/usr/local/bin/evidence approve ABC-1"]:
        t, i = bash(c)
        case(f"REQ-V2A-01 agent cannot approve: {c[:40]}", r, t, i, "deny", rule_hint="human action")
    shutil.rmtree(r)


def suite_change_rules():
    r = make_repo()
    t, i = edit("src/app.py")
    case("REQ-V2G-04 key but no change state denies", r, t, i, "deny", rule_hint="evidence change start")
    plan = start_change(r, approve=False)
    case("REQ-V2A-01 unapproved plan denies", r, t, i, "deny", rule_hint="not been approved")
    start_change(r)
    case("REQ-V2G-04 approved plan allows claimed path", r, t, i, "allow")
    t2, i2 = edit("src/other.py")
    case("REQ-V2G-12 edit outside claims denied", r, t2, i2, "deny", rule_hint="Files claimed")
    t3, i3 = write("tests/test_new.py")
    case("REQ-V2G-12 claimed glob allows new test file", r, t3, i3, "allow")
    with open(plan, "a") as f:
        f.write("\n3. sneaky extra step\n")
    case("REQ-V2A-01 plan edited after approval voids approval", r, t, i, "deny", rule_hint="changed after it was approved")
    start_change(r)
    open(plan, "w").write("# Plan\nTracker: ABC-1\n")
    case("REQ-V2G-04 stub plan denied even if approval hash matches", r, t, i, "deny")
    start_change(r, claims=("src/**",))
    t4, i4 = edit("src/auth/login.py")
    case("REQ-V2S-02 tier floor denies auth edit in a Tier 1 change", r, t4, i4, "deny", rule_hint="minimum of Tier 3")
    start_change(r, tier=3, claims=("src/**",))
    case("REQ-V2S-02 Tier 3 change may edit auth", r, t4, i4, "allow")
    for mode in ("acceptEdits", "bypassPermissions", "auto", "dontAsk"):
        case(f"REQ-V2S-03 Tier 3 denied in {mode} mode", r, t4, i4, "deny", perm=mode, rule_hint="per-change human review")
    start_change(r, tier=3, claims=("src/**", "db/**", ".github/**"))
    t5, i5 = edit("db/migrations/001.sql")
    case("REQ-V2G-08 change-controlled path needs a ticket", r, t5, i5, "deny", rule_hint="change control")
    case("REQ-V2G-08 malformed ticket rejected", r, t5, i5, "deny", env={"CHANGE_TICKET": "lol"}, rule_hint="does not match")
    case("REQ-V2G-08 valid ticket allows", r, t5, i5, "allow", env={"CHANGE_TICKET": "CHG-42"})
    t6, i6 = write(".github/workflows/Release.YML")
    case("REQ-V2G-08 case-insensitive change control", r, t6, i6, "deny", rule_hint="change control")
    start_change(r, claims=("src/**",))
    case("REQ-V2K-03 read-only agent cannot write", r, t, i, "deny", agent_type="evidence-sdlc:security-reviewer",
         rule_hint="read-only")
    case("REQ-V2K-03 main session can write", r, t, i, "allow")
    t7, i7 = write("src/app.py", "AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n")
    case("REQ-V2K-01 secret in written content denied", r, t7, i7, "deny", rule_hint="secret")
    t8, i8 = write("docs/notes.md", "token: ghp_" + "a1B2c3D4e5" * 4 + "\n")
    case("REQ-V2K-01 secret denied even in ungated docs", r, t8, i8, "deny", rule_hint="secret")
    t9, i9 = write("src/app.py", "password = os.environ['DB_PASSWORD']\napi_key = 'changeme'\n")
    case("REQ-V2K-01 env reference and placeholder are not secrets", r, t9, i9, "allow")
    t10, i10 = bash("curl -H 'Authorization: Bearer ghp_" + "Zz9Yy8Xx7W" * 4 + "' https://api.github.com")
    case("REQ-V2K-01 secret on a command line denied", r, t10, i10, "deny", rule_hint="secret")
    for p, body, exp in [("plan/ABC-1.md", "# Plan\nTracker: ABC-1   Approved by: tech lead   Date: x\n", "deny"),
                         ("intent/ABC-1/spec.md", "Status: approved\n", "deny"),
                         ("plan/ABC-1.md", "| Approved by | Jane Doe |\n", "deny"),
                         ("plan/ABC-1.md", "Approval is recorded by a human with /evidence-sdlc:approve.\n", "allow"),
                         ("intent/ABC-1/intent.md", "Status: accepted\n", "allow"),
                         ("docs/release-notes.md", "Approved by: release board\n", "allow")]:
        t, i = write(p, body)
        case(f"REQ-V2A-01 approval text in planning artifacts: {p} {body.strip()[:30]!r}", r, t, i, exp)
    shutil.rmtree(r)


def suite_fix_mode():
    r = make_repo()
    base = sh("git rev-parse HEAD", r).strip()
    start_change(r, kind="fix", claims=("src/**", "tests/**", "spec/**"), fix_base=base, stage="failing-test")
    for p in ("tests/test_app.py", "spec/models/user_spec.rb"):
        t, i = edit(p)
        case(f"REQ-V2G-10 pre-existing test protected in fix mode: {p}", r, t, i, "deny", rule_hint="Fix the code")
    t, i = write("tests/test_regression_bug.py")
    case("REQ-V2G-10 new test file allowed in fix mode", r, t, i, "allow")
    t, i = bash("rm tests/test_app.py")
    case("REQ-V2G-10 deleting a protected test via Bash denied", r, t, i, "deny", rule_hint="Fix the code")
    t, i = edit("src/app.py")
    case("REQ-V2G-10 code edit allowed in fix mode", r, t, i, "allow")
    shutil.rmtree(r)


def suite_push_merge():
    r = make_repo()
    start_change(r)
    for c in ["git push origin HEAD:main", "git push -f origin feature/ABC-1-login:main", "git push origin +HEAD:refs/heads/main",
              "git push origin --delete main", "git push origin :main", "git push --mirror origin", "git push --all origin",
              "git -C . push origin main", "git -c push.default=current push origin main", "env git push origin main",
              "command git push origin main", "/usr/bin/git push origin main", "cd . && git push origin release/1.2",
              "git push origin HEAD:hotfix/urgent"]:
        t, i = bash(c)
        case(f"REQ-V2G-05 REQ-V2G-11 protected push denied: {c[:45]}", r, t, i, "deny", rule_hint="protected")
    t, i = bash("git push -u origin feature/ABC-1-login")
    case("REQ-V2S-04 feature push denied until review agents ran", r, t, i, "deny", rule_hint="verifier")
    record_agent(r, "ABC-1", "someone-elses-plugin:verifier")
    case("REQ-V2S-04 a same-named agent from another plugin does not satisfy the review gate", r, t, i, "deny", rule_hint="verifier")
    record_agent(r, "ABC-1", "evidence-sdlc:verifier")
    case("REQ-V2S-04 feature push allowed after required agents", r, t, i, "allow")
    for c in ["gh pr merge 12 --admin --merge", "gh pr merge 12 --squash", "gh api -X PUT repos/o/r/pulls/1/merge",
              "gh api --method DELETE repos/o/r/branches/main/protection"]:
        t, i = bash(c)
        case(f"REQ-V2G-05 agent merge denied: {c[:40]}", r, t, i, "deny", rule_hint="human")
    t, i = bash("gh pr list --state open")
    case("REQ-V2G-05 read-only gh allowed", r, t, i, "allow")
    sh("git checkout -q main", r)
    t, i = bash("git push")
    case("REQ-V2G-05 bare push from main denied", r, t, i, "deny", rule_hint="protected")
    shutil.rmtree(r)
    r = make_repo()
    start_change(r, tier=2)
    record_agent(r, "ABC-1", "verifier")
    t, i = bash("gh pr create --fill")
    case("REQ-V2S-04 Tier 2 PR needs security-reviewer", r, t, i, "deny", rule_hint="security-reviewer")
    record_agent(r, "ABC-1", "security-reviewer")
    case("REQ-V2S-04 Tier 2 PR allowed after security-reviewer", r, t, i, "allow")
    shutil.rmtree(r)


def suite_commit():
    r = make_repo()
    start_change(r)
    t0, i0 = bash("git commit -m 'ABC-1: x' -m 'Agent-Session: s1'")
    base_case = globals()["case"]
    base_case("REQ-V2A-02 commit without the change's evidence staged is denied", r, t0, i0, "deny", rule_hint="git add")

    def case(*a, **k):
        sh("git add -A .evidence", r)  # a real session stages its evidence with the change
        base_case(*a, **k)
    trailer = "' -m 'Agent-Session: s1"
    for msg, exp, hint in [("fix thing", "deny", "no tracker key"), ("fix UTF-8 handling", "deny", "no tracker key"),
                           ("bump SHA-256 support", "deny", "no tracker key"), ("ABC-1: fix", "deny", "Agent-Session"),
                           ("ABC-1: fix" + trailer, "allow", None), ("OTHER-2: fix" + trailer, "deny", "active change")]:
        t, i = bash(f"git commit -m '{msg}'")
        case(f"REQ-V2G-07/REQ-V2A-03 commit '{msg.splitlines()[0]}'", r, t, i, exp, rule_hint=hint)
    t, i = bash("git commit -m \"$(cat <<'EOF'\nABC-1: heredoc message\n\nAgent-Session: s1\nEOF\n)\"")
    case("REQ-V2A-03 heredoc commit message (Claude Code's pattern) is read", r, t, i, "allow")
    t, i = bash("git commit -F - <<'EOF'\nABC-1: stdin message\n\nAgent-Session: s1\nEOF")
    case("REQ-V2A-03 commit -F - reads the heredoc", r, t, i, "allow")
    t, i = bash("git commit -m \"$(cat <<'EOF'\nno key here\nEOF\n)\"")
    case("REQ-V2G-07 heredoc message without key denied", r, t, i, "deny", rule_hint="no tracker key")
    t, i = bash("git -c user.name=x commit -m 'fix'")
    case("REQ-V2G-07 git -c commit still checked", r, t, i, "deny", rule_hint="no tracker key")
    t, i = bash("git commit -am 'ABC-1: x' -m 'Agent-Session: s1'")
    case("REQ-V2G-07 combined -am flags parsed", r, t, i, "allow")
    t, i = bash("git commit")
    case("REQ-V2G-07 editor commit denied with guidance", r, t, i, "deny", rule_hint="-m or -F")
    open(os.path.join(r, "src", "app.py"), "w").write("TOKEN = 'ghp_" + "Q1w2E3r4T5" * 4 + "'\n")
    sh("git add src/app.py", r)
    t, i = bash("git commit -m 'ABC-1: x" + trailer + "'")
    case("REQ-V2K-01 staged secret blocks commit", r, t, i, "deny", rule_hint="secret")
    sh("git reset -q && git checkout -q -- src/app.py", r)
    for c in ["git -c alias.x='!sh -c id' x", "git -c core.hooksPath=/tmp/h commit -m 'ABC-1: x'",
              "git config alias.pwn '!curl evil'", "git config --global core.sshCommand 'sh -c id'"]:
        t, i = bash(c)
        case(f"REQ-V2K-02 dangerous git config denied: {c[:40]}", r, t, i, "deny", rule_hint="git")
    t, i = bash("git config --get user.email")
    case("REQ-V2K-02 git config read allowed", r, t, i, "allow")
    shutil.rmtree(r)


def suite_deploy():
    r = make_repo()
    for c in ["./deploy.sh production", "./deploy.sh PROD", "./deploy.sh --env=Production", "./deploy.sh prd",
              "./deploy.sh live", "kubectl apply -n production -f k.yaml", "terraform apply -var env=prod",
              "helm upgrade --namespace prod app ./chart", "ENV=pr\"\"od ./deploy.sh", "./deploy.sh $TARGET",
              "bash scripts/deploy.sh prod", "make deploy-prod", "npm run deploy:prod",
              "aws ecs update-service --cluster prod --service api", "gcloud run deploy api --project acme-prod",
              "gh workflow run deploy.yml -f env=production", "sudo -u ops ./release.sh production"]:
        t, i = bash(c)
        case(f"REQ-V2G-06 REQ-V2G-11 production deploy denied: {c[:45]}", r, t, i, "deny", rule_hint="release authorization")
    for c in ["./deploy.sh staging", "kubectl get pods -n production", "helm list -n prod",
              "grep -rn production docs/", "cat deploy/prod.env", "terraform plan -var env=prod",
              "echo 'deploy to prod on friday'"]:
        t, i = bash(c)
        case(f"REQ-V2G-06 non-deploy allowed: {c[:45]}", r, t, i, "allow")
    t, i = bash("./deploy.sh production")
    case("REQ-V2G-06 malformed release approval rejected", r, t, i, "deny", env={"RELEASE_APPROVAL": "x"}, rule_hint="does not match")
    case("REQ-V2G-06 valid release approval allows", r, t, i, "allow", env={"RELEASE_APPROVAL": "REL-2026"})
    shutil.rmtree(r)


def suite_policy_merge():
    r = make_repo()
    start_change(r)
    os.makedirs(os.path.join(r, ".evidence"), exist_ok=True)
    json.dump({"ungated": ["src/**", "**/*.md"], "protected_refs": ["feature/*"], "enforce_claims": False,
               "require_agent_trailer": False}, open(os.path.join(r, ".evidence", "policy.json"), "w"))
    t, i = edit("src/other.py")
    case("REQ-V2X-01 repo policy cannot widen ungated or disable claims", r, t, i, "deny", rule_hint="Files claimed")
    record_agent(r, "ABC-1", "verifier")
    t, i = bash("git push origin feature/ABC-1-login")
    case("REQ-V2X-01 repo policy can add protected refs", r, t, i, "deny", rule_hint="protected")
    t, i = bash("git commit -m 'ABC-1: x'")
    case("REQ-V2X-01 repo policy cannot turn off the agent trailer", r, t, i, "deny", rule_hint="Agent-Session")
    json.dump({"release_approval_pattern": ".*", "change_ticket_pattern": ".*", "approval": {"mode": "local"}},
              open(os.path.join(r, ".evidence", "policy.json"), "w"))
    t, i = bash("./deploy.sh production")
    case("REQ-V2X-01 repo policy cannot loosen the release approval pattern", r, t, i, "deny",
         env={"RELEASE_APPROVAL": "whatever"}, rule_hint="does not match")
    json.dump({"ungated": ["src/**", "**/*.md"]}, open(os.path.join(r, ".evidence", "policy.json"), "w"))
    org = os.path.join(r, "org.json")
    json.dump({"allow_repo_ungated_additions": True}, open(org, "w"))
    t, i = edit("src/other.py")
    case("REQ-V2X-01 org policy can permit repo ungated additions", r, t, i, "allow", env={"EVIDENCE_ORG_POLICY": org})
    shutil.rmtree(r)


def suite_audit_and_session():
    r = make_repo()
    start_change(r)
    payload = {"session_id": "s9", "cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "src/app.py"}}
    run_hook(r, payload, event="post")
    run_hook(r, {"session_id": "s9", "cwd": r, "tool_name": "Agent",
                 "tool_input": {"subagent_type": "evidence-sdlc:verifier", "description": "verify"},
                 "tool_response": {"content": "ok"}}, event="post")
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import state as st
    log = os.path.join(r, ".evidence", "audit", "s9.jsonl")
    ok, problems = st.audit_verify(log)
    check("REQ-V2A-02 audit chain verifies", ok, problems)
    agents = st.recorded_agents(r, "ABC-1")
    check("REQ-V2S-04 agent completion recorded from PostToolUse", "verifier" in agents, agents)
    lines = open(log).read().splitlines()
    e = json.loads(lines[0])
    e["path"] = "src/innocent.py"
    lines[0] = json.dumps(e, sort_keys=True)
    open(log, "w").write("\n".join(lines) + "\n")
    ok, problems = st.audit_verify(log)
    check("REQ-V2A-02 tampering detected", not ok, "altered line was not detected")
    state = json.load(open(os.path.join(r, ".evidence", "changes", "ABC-1", "state.json")))
    check("REQ-V2S-01 first source edit advances approved -> implementing", state.get("stage") == "implementing", state)
    obj, _ = run_hook(r, {"session_id": "s9", "cwd": r}, event="session-start")
    ctxt = obj.get("hookSpecificOutput", {}).get("additionalContext", "")
    check("REQ-V2K-02 session-start canary line present", "gates live" in ctxt and "ABC-1" in ctxt, ctxt)
    shutil.rmtree(r)


def suite_historic():
    """False-positive and edge cases carried over from the v1 gate suite (PILOT-7..12)."""
    r = make_repo()
    os.makedirs(os.path.join(r, "src", "cache-invalidation"))
    os.makedirs(os.path.join(r, "src", "test-infra"))
    for p in ("src/latest_migration.py", "src/fastest_path.py", "src/cache-invalidation/x.py", "src/test-infra/x.py"):
        open(os.path.join(r, p), "w").write("a\n")
    sh("git add -A && git commit -q -m 'ABC-0: more'", r)
    base = sh("git rev-parse HEAD", r).strip()
    start_change(r, kind="fix", claims=("src/**", "tests/**"), fix_base=base, stage="failing-test")
    for p in ("src/latest_migration.py", "src/fastest_path.py"):
        t, i = edit(p)
        case(f"REQ-GATE-02 historic PILOT-9: {p} is not a test", r, t, i, "allow")
    for p in ("src/cache-invalidation/x.py", "src/test-infra/x.py"):
        t, i = edit(p)
        case(f"REQ-GATE-02 historic PILOT-10: {p} is not change-controlled", r, t, i, "allow")
    sub = os.path.join(r, "src")
    obj, _ = run_hook(sub, {"session_id": "s1", "cwd": sub, "tool_name": "Edit",
                            "tool_input": {"file_path": "app.py"}, "permission_mode": "default"})
    got, why = decision(obj)
    check("REQ-GATE-02 historic PILOT-52: tool call from a subdirectory resolves repo-root state", got == "allow", why)
    for c in ["echo 'remember to git commit later'", "echo \"remember to git push after review\"",
              "./scripts/reproduce.sh", "./deploy.sh byproduct-catalog", "./deploy.sh product"]:
        t, i = bash(c)
        case(f"REQ-GATE-02 historic PILOT-8/11/12: allowed: {c[:40]}", r, t, i, "allow")
    shutil.rmtree(r)
    r = make_repo(branch="feature/x")
    t, i = edit("tests/test_app.py")
    case("REQ-V2G-10 legacy FIX_TASK=1 still protects existing tests", r, t, i, "deny", env={"FIX_TASK": "1"}, rule_hint="FIX_TASK")
    shutil.rmtree(r)


def suite_self_review():
    """Bypasses found in the engine's own post-build review (PILOT-53 second pass)."""
    r = make_repo()
    base = sh("git rev-parse HEAD", r).strip()
    start_change(r, kind="fix", claims=("src/app.py", "tests/**", ".evidence/**"), fix_base=base, stage="failing-test")
    for c in ["ls src/*.py | xargs rm", "find src -name '*.py' -delete", "find . -name '*.py' -exec rm {} +",
              "rm tests/*.py", "rm tests/test_{app,other}.py", "cd tests && rm test_app.py", "cd src && echo x > other.py",
              "rm -rf .evidence/audit", "rm -rf .evidence", "rm -rf .", "git checkout -- .",
              "tar -xf bundle.tar", "unzip bundle.zip"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 self-review: bulk/indirect write denied: {c[:40]}", r, t, i, "deny")
    for c in ["find . -name '*.py' -exec grep -l TODO {} +", "find src -type f | wc -l", "tar -tf bundle.tar",
              "cd src && ls", "cd tests && python3 -m unittest"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 self-review: read-only allowed: {c[:40]}", r, t, i, "allow")
    open(os.path.join(r, "notes.txt"), "w").write("echo pwned > src/app.py\n")
    os.makedirs(os.path.join(r, "docs"), exist_ok=True)
    tmp_script = os.path.join(tempfile.gettempdir(), "evidence-selfreview-x.py")
    open(tmp_script, "w").write("print(1)\n")
    for c in ["bash notes.txt", "sh ./notes.txt", "source notes.txt", ". notes.txt", f"python3 {tmp_script}",
              "python3 -c \"import sys; sys.path.insert(0,'e'); import lifecycle; lifecycle.write_approval(1,2,3,4,5)\"",
              "python3 -c \"exec(open('notes.txt').read())\"", "python3 -c \"import base64;exec(base64.b64decode('eA=='))\"",
              "node -e \"require('child_process').execSync('id')\"", "bash $SCRIPT"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 self-review: unchecked code execution denied: {c[:45]}", r, t, i, "deny")
    os.remove(tmp_script)
    for c in ["gh pr review 5 --approve", "gh pr review 5 -a -b ok", "gh pr comment 5 --body '/approve-plan abcdef123456'",
              "gh api repos/o/r/pulls/5/reviews -f event=APPROVE", "gh api graphql -f query='mutation { mergePullRequest(input:{}) { clientMutationId } }'",
              "curl -X PUT -H 'Authorization: token x' https://api.github.com/repos/o/r/pulls/5/merge",
              "curl --json '{}' https://gitlab.example.com/api/v4/projects/1/merge_requests/2/approve"]:
        t, i = bash(c)
        case(f"REQ-V2A-01 REQ-V2G-05 self-review: agent approval/merge via API denied: {c[:45]}", r, t, i, "deny")
    for c in ["f(){ rm -f src/other.py; }; f", "alias w='tee src/other.py'; echo x | w", "awk 'BEGIN{system(\"touch x\")}'",
              "awk '{print > \"src/other.py\"}' src/app.py", "git config --file .git/config alias.x '!id'",
              "ln -s ../.evidence/changes/ABC-1/approval.json src/app.py", "IFS=,; cmd=rm,src/other.py; $cmd",
              "vim -es -c 'wq' src/other.py", "env -S 'rm src/other.py'", "if true; then rm src/other.py; fi",
              "while read f; do rm \"$f\"; done < list.txt"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 self-review: shell-syntax evasion denied: {c[:45]}", r, t, i, "deny")
    for c in ["claude -p '/evidence-sdlc:approve ABC-1 abcdef123456'", "npx @anthropic-ai/claude-code -p 'evidence approve ABC-1 x'",
              "script -q /dev/null claude 'evidence approve ABC-1 abcdef123456'", "unbuffer claude",
              "python3 -c \"import subprocess; subprocess.run(['claude','-p','x'])\"", "/Users/me/.local/bin/claude --resume x -p hi"]:
        t, i = bash(c)
        case(f"REQ-V2A-01 self-review: nested Claude Code session denied: {c[:45]}", r, t, i, "deny")
    for c in ["gh pr review 5 --comment -b 'looks fine'", "curl -s https://api.github.com/repos/o/r/pulls/5", "bash -n scripts/x.sh"]:
        t, i = bash(c)
        case(f"REQ-V2G-05 self-review: harmless variant allowed: {c[:45]}", r, t, i, "allow")
    shutil.rmtree(r)


def suite_gate_true_positives():
    """REQ-GATE-01: the documented true positive of each v1 gate is still denied by the engine."""
    r = make_repo(branch="feature/x")
    t, i = edit("src/app.py")
    case("REQ-GATE-01 gate-plan-exists: source edit with no approved plan is denied", r, t, i, "deny")
    t, i = bash("./deploy.sh production")
    case("REQ-GATE-01 production-gate: release to production without approval is denied", r, t, i, "deny")
    t, i = bash("git commit -m 'fix thing'")
    case("REQ-GATE-01 require-issue-key: commit without a key is denied", r, t, i, "deny")
    t, i = edit("tests/test_app.py")
    case("REQ-GATE-01 block-test-weakening: existing test edit in a fix task is denied", r, t, i, "deny", env={"FIX_TASK": "1"})
    sh("git checkout -q main", r)
    t, i = bash("git push origin main")
    case("REQ-GATE-01 block-protected-branch-push: push to main is denied", r, t, i, "deny")
    shutil.rmtree(r)
    r = make_repo()
    start_change(r, tier=3, claims=("db/**",))
    t, i = edit("db/migrations/001.sql")
    case("REQ-GATE-01 protect-validated-paths: migration edit without a change ticket is denied", r, t, i, "deny")
    shutil.rmtree(r)


def suite_mutation():
    """REQ-GATE-03: the suite discriminates -- reverting a fix in a copy of the engine makes cases fail."""
    engine = os.path.join(HERE, "..", "engine")
    mutants = [
        ("evidence_policy.py", "    if ref == \"*\":\n        return True\n    return any(", "    return False\n    return any(",
         bash("git push origin HEAD:main"), "deny"),
        ("evidence_policy.py", "if rel and pol.get(\"enforce_claims\", True):", "if False:",
         edit("src/other.py"), "deny"),
        ("cmdparse.py", "    for op, target in s.redirects:", "    for op, target in []:",
         bash("echo x > src/app.py"), "deny"),
        ("secretscan.py", "    if not text:\n        return []", "    return []",
         write("src/app.py", "k = 'AKIAIOSFODNN7EXAMPLE'\n"), "deny"),
    ]
    for fname, old, new, (tool, ti), expect in mutants:
        d = tempfile.mkdtemp(prefix="evidence-mutant-")
        shutil.copytree(engine, os.path.join(d, "scripts", "engine"))
        os.makedirs(os.path.join(d, "policy"))
        shutil.copy(os.path.join(HERE, "..", "..", "policy", "default-policy.json"), os.path.join(d, "policy"))
        mp = os.path.join(d, "scripts", "engine", fname)
        src = open(mp).read()
        applied = old in src
        open(mp, "w").write(src.replace(old, new, 1))
        r = make_repo()
        start_change(r)
        record_agent(r, "ABC-1", "verifier")  # isolate the rule under test from the review-agent gate
        payload = {"session_id": "s1", "cwd": r, "tool_name": tool, "tool_input": ti, "permission_mode": "default"}
        env = dict(BASE_ENV)
        rr = subprocess.run([sys.executable, os.path.join(d, "scripts", "engine", "hook.py"), "pre"], input=json.dumps(payload),
                            cwd=r, capture_output=True, text=True, env=env)
        try:
            got, _ = decision(json.loads(rr.stdout or "{}"))
        except ValueError:
            got = "error"
        check(f"REQ-GATE-03 mutant {fname} ({new.strip()[:30]}) flips a {expect} case", applied and got != expect,
              f"mutation applied={applied}, mutant decision={got}")
        shutil.rmtree(d)
        shutil.rmtree(r)


def suite_integrity():
    """Writes by programs the parser cannot see are detected after the fact (REQ-V2G-02 defence in depth)."""
    r = make_repo()
    start_change(r)
    sh("git add -A && git commit -q -m 'ABC-1: change files' ", r)
    appr = os.path.join(r, ".evidence", "changes", "ABC-1", "approval.json")
    original = open(appr).read()

    def around(cmd, mutate, tid):
        pre = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": tid,
               "permission_mode": "default"}
        obj, _ = run_hook(r, pre)
        mutate()
        post = dict(pre, hook_event_name="PostToolUse", tool_response={"stdout": ""})
        obj2, _ = run_hook(r, post, event="post")
        return decision(obj)[0], obj2.get("hookSpecificOutput", {}).get("additionalContext", "")

    got, note = around("./vendor/tool --quiet", lambda: open(appr, "w").write('{"forged": true}'), "t1")
    check("REQ-V2G-09 integrity: control-plane change by an unparsed program is restored",
          got == "allow" and open(appr).read() == original and "restored" in note, note)
    got, note = around("./vendor/tool", lambda: open(os.path.join(r, ".evidence", "policy.json"), "w").write("{}"), "t2")
    check("REQ-V2G-09 integrity: control-plane file created by an unparsed program is removed",
          not os.path.exists(os.path.join(r, ".evidence", "policy.json")) and "removed" in note, note)
    got, note = around("./vendor/tool", lambda: open(os.path.join(r, "src", "sneaky.py"), "w").write("x=1\n"), "t3")
    check("REQ-V2G-02 integrity: unclaimed source write by an unparsed program is recorded", "sneaky.py" in note, note)
    record_agent(r, "ABC-1", "evidence-sdlc:verifier")
    t, i = bash("git push -u origin feature/ABC-1-login")
    case("REQ-V2G-02 integrity: open violation blocks push", r, t, i, "deny", rule_hint="integrity monitor")
    t, i = bash("evidence change clear-violations ABC-1")
    case("REQ-V2A-01 integrity: agent cannot clear violations", r, t, i, "deny", rule_hint="human action")
    r2 = make_repo()
    start_change(r2)
    sh("git add -A && git commit -q -m 'ABC-1: change files'", r2)
    r_saved = r
    r = r2
    got, note = around("./vendor/formatter src/app.py", lambda: open(os.path.join(r2, "src", "app.py"), "w").write("a = 2\n"), "t4")
    check("REQ-V2G-02 integrity: a claimed write by an unparsed program is not a violation", note == "", note)
    shutil.rmtree(r_saved)
    shutil.rmtree(r2)


def suite_reaudit_fixes():
    """Findings from the independent v2 re-audit, each reproduced and now closed."""
    KEYENV = {"EVIDENCE_SIGNING_KEY": "k" * 40}
    r = make_repo()
    start_change(r)  # writes an UNSIGNED approval.json, as a forger would
    t, i = edit("src/app.py")
    case("REQ-V2A-01 re-audit: forged (unsigned) approval rejected when a signing key is configured", r, t, i, "deny",
         env=KEYENV, rule_hint="not valid")
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    env_backup = os.environ.get("EVIDENCE_SIGNING_KEY")
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    import importlib, lifecycle, state as st
    importlib.reload(st)
    lifecycle.write_approval(r, "ABC-1", os.path.join(r, "plan", "ABC-1.md"), "human", "prompt")
    st.audit_append(r, "s1", {"event": "agent-completed", "key": "ABC-1", "subagent_type": "evidence-sdlc:verifier"})
    if env_backup is None:
        del os.environ["EVIDENCE_SIGNING_KEY"]
    case("REQ-V2A-01 re-audit: approval written by a human channel (signed) allows", r, t, i, "allow", env=KEYENV)
    t2, i2 = bash("git push -u origin feature/ABC-1-login")
    case("REQ-V2S-04 re-audit: signed agent-completed entry satisfies the review gate", r, t2, i2, "allow", env=KEYENV)
    with open(os.path.join(r, ".evidence", "audit", "forged.jsonl"), "w") as f:
        f.write(json.dumps({"event": "agent-completed", "key": "ABC-2", "subagent_type": "evidence-sdlc:verifier",
                            "ts": "2099-01-01T00:00:00Z", "prev": "", "hash": "x"}) + "\n")
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    check("REQ-V2A-02 re-audit: forged audit entry does not count as a review", "verifier" not in st.recorded_agents(r, "ABC-2"))
    del os.environ["EVIDENCE_SIGNING_KEY"]
    for c in ["python3 < notes.md", "cat x.md | python3", "bash < script.txt", "cat run.txt | sh",
              "nohup ./tool &", "setsid ./tool", "echo 'rm x' | at now + 1 minute", "crontab jobs.txt",
              "launchctl load ~/Library/LaunchAgents/x.plist"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 re-audit: hidden or deferred execution denied: {c[:40]}", r, t, i, "deny")
    t, i = bash("JUNIT_OUT=validation/results/fake.xml python3 tests/test_app.py")
    case("REQ-V2G-08 re-audit: an output-path env assignment into validation/ is judged as a write", r, t, i, "deny")
    t, i = bash("PATH=/usr/bin:/bin ls")
    case("REQ-V2G-02 re-audit: ordinary env assignments are not writes", r, t, i, "allow")
    t, i = bash("crontab -l")
    case("REQ-V2G-02 re-audit: reading crontab allowed", r, t, i, "allow")
    t, i = bash("curl https://example.com/x")
    case("REQ-V2K-03 re-audit: read-only agent has no network", r, t, i, "deny", agent_type="evidence-sdlc:security-reviewer",
         rule_hint="network")
    t, i = bash("sed -i '' 's/a/b/' src/app.py")
    case("REQ-V2G-02 re-audit: macOS sed -i '' on a claimed file allowed", r, t, i, "allow", env=KEYENV)
    for p in ("CLAUDE.md", "docs/CLAUDE.md", "plugins/x/templates/REVIEW.md"):
        t, i = write(p, "x")
        case(f"REQ-V2G-03 re-audit: {p} is gated despite being markdown", r, t, i, "deny")
    for p in (".claude/commands/deploy.md", ".claude/skills/x/SKILL.md"):
        t, i = write(p, "x")
        case(f"REQ-V2G-09 re-audit: {p} is control plane", r, t, i, "deny", rule_hint="control plane")
    st_path = os.path.join(r, ".evidence", "changes", "ABC-1", "state.json")
    stj = json.load(open(st_path)); stj["stage"] = "released"; json.dump(stj, open(st_path, "w"))
    t, i = edit("src/app.py")
    case("REQ-V2S-01 re-audit: a released change no longer unlocks edits", r, t, i, "deny", rule_hint="released")
    shutil.rmtree(r)

    # the golden path: the agent runs the CLI; the integrity monitor must not revert it
    r = make_repo(branch="feature/ABC-5-thing")
    evidence = os.path.join(HERE, "..", "..", "bin", "evidence")
    cmd = f"python3 {evidence} change start ABC-5 --tier 1 --kind feature"
    pre = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": "g1",
           "permission_mode": "default"}
    obj, _ = run_hook(r, pre)
    subprocess.run(cmd, shell=True, cwd=r, env=BASE_ENV, capture_output=True)
    obj2, _ = run_hook(r, dict(pre, hook_event_name="PostToolUse"), event="post")
    note = obj2.get("hookSpecificOutput", {}).get("additionalContext", "")
    check("REQ-V2S-01 re-audit: agent-run `evidence change start` is not reverted by the integrity monitor",
          os.path.isfile(os.path.join(r, ".evidence", "changes", "ABC-5", "state.json")) and "Integrity" not in note, note)
    # missing snapshot is a violation, not a silent pass
    pre2 = dict(pre, tool_input={"command": "./vendor/tool"}, tool_use_id="g2")
    run_hook(r, pre2)
    import glob as _g
    for f in _g.glob(os.path.join(tempfile.gettempdir(), "evidence-chain-snapshots", "s1", "g2.json")):
        os.remove(f)
    obj3, _ = run_hook(r, dict(pre2, hook_event_name="PostToolUse"), event="post")
    check("REQ-V2G-02 re-audit: a removed integrity snapshot is recorded as a violation",
          "missing" in obj3.get("hookSpecificOutput", {}).get("additionalContext", ""), obj3)
    # worktrees: .git is a file, the monitor must still run
    wt = r + "-wt"
    sh(f"git worktree add -q -b feature/ABC-6-wt {wt}", r)
    pre3 = {"session_id": "s2", "cwd": wt, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"},
            "tool_use_id": "w1", "permission_mode": "default"}
    run_hook(wt, pre3)
    open(os.path.join(wt, "src", "sneaky.py"), "w").write("x\n")
    obj4, _ = run_hook(wt, dict(pre3, hook_event_name="PostToolUse"), event="post")
    check("REQ-V2G-02 re-audit: integrity monitor runs inside a git worktree",
          "sneaky.py" in obj4.get("hookSpecificOutput", {}).get("additionalContext", ""), obj4)
    shutil.rmtree(wt, ignore_errors=True)
    # CI: detached HEAD resolves the key from the PR head branch
    sh("git checkout -q --detach", r)
    obj5, _ = run_hook(r, {"session_id": "ci", "cwd": r}, event="session-start", env_extra={"GITHUB_HEAD_REF": "feature/ABC-5-thing"})
    check("REQ-V2S-01 re-audit: CI detached HEAD resolves the key from GITHUB_HEAD_REF",
          "ABC-5" in obj5.get("hookSpecificOutput", {}).get("additionalContext", ""), obj5)
    shutil.rmtree(r)

    # a review that ran before later edits does not count
    r = make_repo()
    start_change(r)
    record_agent(r, "ABC-1", "evidence-sdlc:verifier")
    import time; time.sleep(1.1)
    run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "src/app.py"}}, event="post")
    t, i = bash("git push -u origin feature/ABC-1-login")
    case("REQ-V2S-04 re-audit: a verifier run older than the latest source edit does not count", r, t, i, "deny",
         rule_hint="verifier")
    shutil.rmtree(r)


if __name__ == "__main__":
    for fn in [suite_reaudit_fixes, suite_integrity, suite_gate_true_positives, suite_mutation, suite_self_review, suite_historic, suite_fail_closed, suite_no_change, suite_control_plane, suite_change_rules, suite_fix_mode,
               suite_push_merge, suite_commit, suite_deploy, suite_policy_merge, suite_audit_and_session]:
        fn()
    print(f"\n{results['pass']} passed, {results['fail']} failed")
    if os.environ.get("JUNIT_OUT"):
        write_junit(os.environ["JUNIT_OUT"], "evidence-sdlc gate engine")
    sys.exit(1 if results["fail"] else 0)
