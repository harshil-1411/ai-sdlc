#!/usr/bin/env python3
"""Regression suite for the v2 gate engine (PILOT-53).

Every probe from the v1 enterprise audit's security table is a case here, run
exactly as Claude Code runs the hook: a JSON payload on stdin to hook.py, in a
throwaway git repository. Cases are grouped by requirement ID. Run:

    python3 plugins/evidence-sdlc/scripts/tests/engine-tests.py [-v] [-k substring]
"""
import glob
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
                         "EVIDENCE_ACTIVE_CHANGE", "EVIDENCE_ORG_POLICY", "FIX_TASK", "EVIDENCE_SIGNING_KEY",
                         "GITHUB_HEAD_REF")}
BASE_ENV["GIT_AUTHOR_NAME"] = BASE_ENV["GIT_COMMITTER_NAME"] = "test"
BASE_ENV["GIT_AUTHOR_EMAIL"] = BASE_ENV["GIT_COMMITTER_EMAIL"] = "test@example.com"
# Most suites run without a signing key, so the fixture org policy opts in to unsigned
# Tier 2/3 (the default allows only Tier 1 unsigned). suite_round5 tests the default.
_ORG = os.path.join(tempfile.gettempdir(), "evidence-test-org-policy.json")
json.dump({"unsigned_max_tier": 3}, open(_ORG, "w"))
BASE_ENV["EVIDENCE_ORG_POLICY"] = _ORG

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
    env["CLAUDE_PROJECT_DIR"] = repo  # Claude Code sets it for every hook
    env.update(env_extra or {})
    env = {k: v for k, v in env.items() if v is not None}
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
    t, i = bash("git -c core.quotepath=off commit -m 'fix'")
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
    json.dump({"allow_repo_ungated_additions": True, "unsigned_max_tier": 3}, open(org, "w"))
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

    KEY = {"EVIDENCE_SIGNING_KEY": "k" * 40}

    def around(cmd, mutate, tid, env=None):
        pre = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": tid,
               "permission_mode": "default"}
        obj, _ = run_hook(r, pre, env_extra=env)
        mutate()
        post = dict(pre, hook_event_name="PostToolUse", tool_response={"stdout": ""})
        obj2, _ = run_hook(r, post, event="post", env_extra=env)
        return decision(obj)[0], obj2.get("hookSpecificOutput", {}).get("additionalContext", "")

    got, note = around("./vendor/tool --quiet", lambda: open(appr, "w").write('{"forged": true}'), "t0")
    check("REQ-V2G-09 integrity: in unsigned mode a control-plane change is recorded, never restored from an unsigned snapshot",
          "was changed" in note and "restored" not in note, note)
    open(appr, "w").write(original)
    got, note = around("./vendor/tool --quiet", lambda: open(appr, "w").write('{"forged": true}'), "t1", env=KEY)
    check("REQ-V2G-09 integrity: control-plane change by an unparsed program is restored (signed snapshot)",
          got == "allow" and open(appr).read() == original and "restored" in note, note)
    got, note = around("./vendor/tool", lambda: open(os.path.join(r, ".evidence", "policy.json"), "w").write("{}"), "t2", env=KEY)
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
    case("REQ-V2A-01 re-audit: unsigned lifecycle state rejected when a signing key is configured", r, t, i, "deny",
         env=KEYENV, rule_hint="not signed")
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import state as _st0
    _st0.save_state(r, "ABC-1", json.load(open(os.path.join(r, ".evidence", "changes", "ABC-1", "state.json"))))
    del os.environ["EVIDENCE_SIGNING_KEY"]
    case("REQ-V2A-01 re-audit: forged (unsigned) approval rejected when a signing key is configured", r, t, i, "deny",
         env=KEYENV, rule_hint="not valid")
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    env_backup = os.environ.get("EVIDENCE_SIGNING_KEY")
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    import importlib, lifecycle, state as st
    importlib.reload(st)
    st.save_state(r, "ABC-1", json.load(open(os.path.join(r, ".evidence", "changes", "ABC-1", "state.json"))))
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

    # the golden path: the agent asks for `evidence change start`; the hook performs it (PILOT-57), and
    # Claude Code neither runs the command nor calls PostToolUse, so there is nothing for the monitor to revert
    r = make_repo(branch="feature/ABC-5-thing")
    evidence = os.path.join(HERE, "..", "..", "bin", "evidence")
    cmd = f"python3 {evidence} change start ABC-5 --tier 1 --kind feature"
    pre = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": "g1",
           "permission_mode": "default"}
    obj, _ = run_hook(r, pre)
    check("REQ-V2S-01 re-audit: agent-run `evidence change start` creates the change (performed by the hook)",
          os.path.isfile(os.path.join(r, ".evidence", "changes", "ABC-5", "state.json"))
          and "Done by the gate engine" in decision(obj)[1], obj)
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
    obj5, _ = run_hook(r, {"session_id": "ci", "cwd": r}, event="session-start", env_extra={"GITHUB_HEAD_REF": "feature/ABC-5-thing", "GITHUB_ACTIONS": "true"})
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


def suite_round4():
    """Defects reproduced by the final independent verification (round 4)."""
    r = make_repo()
    start_change(r, claims=("src/app.py", "tests/**"))
    deny_cmds = ["sleep 3 &", "(sleep 1; cp /tmp/x src/other.py) &", "screen -dm sh -c 'rm src/other.py'",
                 "tmux new -d 'x'", "caffeinate -i ./tool", "python3 /dev/stdin < notes.md", "exec 3<x.md; python3 <&3",
                 "python3 <(cat x.md)", "python3 -c \"$(cat x.md)\"", "export JUNIT_OUT=validation/results/x.xml; pytest",
                 "pytest --junitxml=validation/results/x.xml", "ditto /tmp/evil src/other", "busybox sh -c 'rm src/other.py'",
                 "sqlite3 src/other.db 'create table t(x)'", "osascript -e 'do shell script \"id\"'",
                 "make -f /tmp/Makefile", "git remote set-url origin https://github.com/evil/repo",
                 "gh repo set-default evil/repo", "echo $EVIDENCE_SIGNING_KEY", "printenv", "ps eww",
                 "python3 -c 'import os; print(os.environ)'", "cat '/Library/Application Support/ClaudeCode/managed-settings.json'"]
    for c in deny_cmds:
        t, i = bash(c)
        case(f"REQ-V2G-02 round4: denied: {c[:48]}", r, t, i, "deny")
    for c in ["npm test && echo ok", "ls 2>&1 | head", "make test > /dev/null 2>&1", "sed -i '' -e 's/a/b/' src/app.py",
              "git remote -v", "gh repo view"]:
        t, i = bash(c)
        case(f"REQ-V2G-02 round4: allowed: {c[:48]}", r, t, i, "allow")
    case("REQ-V2K-01 round4: Read of managed settings denied", r, "Read",
         {"file_path": "/Library/Application Support/ClaudeCode/managed-settings.json"}, "deny", rule_hint="not readable")
    case("REQ-V2K-01 round4: ordinary Read allowed", r, "Read", {"file_path": "src/app.py"}, "allow")
    plan = os.path.join(r, "plan", "ABC-1.md")
    text = open(plan).read()
    for bad, label in ((text.replace("Risk tier: 1", ""), "missing"), (text + "\nRisk tier: 2\n", "twice")):
        open(plan, "w").write(bad)
        start_change(r, claims=("src/app.py", "tests/**")) if False else None
        sha = hashlib.sha256(open(plan, "rb").read()).hexdigest()
        ap = os.path.join(r, ".evidence", "changes", "ABC-1", "approval.json")
        a = json.load(open(ap)); a["plan_sha256"] = sha; json.dump(a, open(ap, "w"))
        t, i = edit("src/app.py")
        case(f"REQ-V2S-02 round4: plan tier line {label} is denied", r, t, i, "deny", rule_hint="Risk tier")
    start_change(r, claims=("src/app.py", "tests/**"))
    sh("git add -A .evidence", r)
    open(os.path.join(r, "src", "unclaimed.py"), "w").write("x\n")
    sh("git add src/unclaimed.py", r)
    t, i = bash("git commit -m 'ABC-1: x' -m 'Agent-Session: s1'")
    case("REQ-V2G-12 round4: a commit staging an unclaimed file is denied", r, t, i, "deny", rule_hint="outside the approved plan")
    sh("git reset -q src/unclaimed.py && rm src/unclaimed.py && git add -A .evidence && git commit -q -m 'ABC-1: evidence' -m 'Agent-Session: s1'", r)
    with open(os.path.join(r, ".evidence", "audit", "s1.jsonl"), "a") as f:
        f.write("")
    run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "src/app.py"}}, event="post")
    t, i = bash("git commit -m 'ABC-1: y' -m 'Agent-Session: s1'")
    case("REQ-V2A-02 round4: a later commit with the audit log modified but unstaged is denied", r, t, i, "deny", rule_hint="git add")
    # snapshot replay
    pre_a = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"}, "tool_use_id": "ra",
             "permission_mode": "default"}
    run_hook(r, pre_a)
    d = os.path.join(tempfile.gettempdir(), "evidence-chain-snapshots", "s1")
    pre_b = dict(pre_a, tool_use_id="rb")
    run_hook(r, pre_b)
    shutil.copy(os.path.join(d, "ra.json"), os.path.join(d, "rb.json"))
    obj, _ = run_hook(r, dict(pre_b, hook_event_name="PostToolUse"), event="post")
    check("REQ-V2G-02 round4: a replayed integrity snapshot is recorded as a violation",
          "replayed" in obj.get("hookSpecificOutput", {}).get("additionalContext", ""), obj)
    shutil.rmtree(r)
    # --quick fast path is not a violation, and the plugin's own CLI may run from anywhere
    r = make_repo(branch="feature/ABC-8-quick")
    evidence = os.path.realpath(os.path.join(HERE, "..", "..", "bin", "evidence"))
    cmd = f"python3 {evidence} change start ABC-8 --tier 1 --quick 'fix typo' --files src/app.py"
    pre = {"session_id": "s3", "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": "q1",
           "permission_mode": "default"}
    obj0, _ = run_hook(r, pre)
    check("REQ-V2S-01 round4: the plugin's own CLI is recognised wherever the plugin is installed; an agent's "
          "`--quick` is refused with guidance (PILOT-57: the hook writes only state.json)",
          "Write the plan with the Write tool" in decision(obj0)[1] and not os.path.exists(os.path.join(r, "plan")), obj0)
    human = {k: v for k, v in BASE_ENV.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    subprocess.run(cmd, shell=True, cwd=r, env=human, capture_output=True)
    check("REQ-V2S-01 round4: `change start --quick` from a human terminal creates the plan",
          os.path.isfile(os.path.join(r, "plan", "ABC-8.md")))
    t, i = bash(f"python3 {evidence} change status ABC-8")
    case("REQ-V2S-01 round4: read-only CLI calls still run in the agent's shell", r, t, i, "allow")
    shutil.rmtree(r)


def suite_round5():
    """Round 5: unsigned-mode limits, Tier 3 second person, hidden changes, strict mode."""
    r = make_repo()
    start_change(r, tier=2, claims=("src/**",))
    t, i = edit("src/app.py")
    case("REQ-V2A-01 round5: by default an unsigned session cannot work on a Tier 2 change", r, t, i, "deny",
         env={"EVIDENCE_ORG_POLICY": "/nonexistent"}, rule_hint="UNSIGNED MODE")
    start_change(r, tier=3, claims=("src/**",))
    st_p = os.path.join(r, ".evidence", "changes", "ABC-1", "state.json")
    ap_p = os.path.join(r, ".evidence", "changes", "ABC-1", "approval.json")
    stj = json.load(open(st_p)); stj["created_by"] = "dev@example.com"; json.dump(stj, open(st_p, "w"))
    apj = json.load(open(ap_p)); apj["approver"] = "dev@example.com"; apj["method"] = "prompt"; json.dump(apj, open(ap_p, "w"))
    case("REQ-V2A-01 round5: Tier 3 plan approved by the person who started the change is denied", r, t, i, "deny",
         rule_hint="second person")
    apj["approver"] = "lead@example.com"; json.dump(apj, open(ap_p, "w"))
    case("REQ-V2A-01 round5: Tier 3 plan approved by a second person is allowed", r, t, i, "allow")
    t2, i2 = write(".gitignore", "*\n")
    case("REQ-V2G-03 round5: .gitignore is gated (it controls what the monitor can see)", r, t2, i2, "deny")
    sh("git add -A && git commit -q -m 'ABC-1: c'", r)
    for tid, mut, label in (
            ("h1", lambda: sh("git update-index --assume-unchanged src/app.py", r), "an index flag hiding edits"),
            ("h2", lambda: open(os.path.join(r, ".git", "hooks", "pre-commit"), "w").write("#!/bin/sh\n"), "a new git hook"),
            ("h3", lambda: open(os.path.join(r, ".git", "info", "exclude"), "a").write("src/\n"), "git exclude rules")):
        pre = {"session_id": "s5", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"}, "tool_use_id": tid,
               "permission_mode": "default"}
        run_hook(r, pre)
        mut()
        obj, _ = run_hook(r, dict(pre, hook_event_name="PostToolUse"), event="post")
        check(f"REQ-V2G-02 round5: integrity monitor records {label}",
              "outside what git status shows" in obj.get("hookSpecificOutput", {}).get("additionalContext", ""), obj)
    for c in ["GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=user.email GIT_CONFIG_VALUE_0=bot@x evidence change start ABC-7 --tier 3",
              "GIT_AUTHOR_EMAIL=boss@corp.com git commit -m 'ABC-1: x'", "git config user.email boss@corp.com",
              "git -c user.email=boss@corp.com commit -m 'ABC-1: x'"]:
        t5, i5 = bash(c)
        case(f"REQ-V2A-01 round6: identity spoofing denied: {c[:45]}", r, t5, i5, "deny", rule_hint="identity")
    t5, i5 = bash("git config --get user.email")
    case("REQ-V2A-01 round6: reading git identity allowed", r, t5, i5, "allow")
    strict = os.path.join(r, "strict.json")
    json.dump({"unknown_programs": "deny", "unsigned_max_tier": 3}, open(strict, "w"))
    t3, i3 = bash("./vendor/mystery-binary --flag")
    case("REQ-V2X-01 round5: strict mode denies an unknown program", r, t3, i3, "deny", env={"EVIDENCE_ORG_POLICY": strict},
         rule_hint="known programs")
    t4, i4 = bash("pytest -q tests")
    case("REQ-V2X-01 round5: strict mode allows a known program", r, t4, i4, "allow", env={"EVIDENCE_ORG_POLICY": strict})
    shutil.rmtree(r)


def suite_signed_lifecycle():
    """PILOT-57: defects found by the first real signed-deployment session (spec D2-D6)."""
    KEY = {"EVIDENCE_SIGNING_KEY": "k" * 40}
    NOORG = {"EVIDENCE_ORG_POLICY": "/nonexistent"}  # the default: unsigned sessions stop at Tier 1
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import importlib
    import signing
    evidence = os.path.realpath(os.path.join(HERE, "..", "..", "bin", "evidence"))

    def pre_post(r, cmd, tid, env=None, mutate=None, session="s7"):
        pre = {"session_id": session, "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": tid,
               "permission_mode": "default"}
        obj, _ = run_hook(r, pre, env_extra=env)
        if decision(obj)[0] == "deny":  # Claude Code runs neither the command nor PostToolUse
            return decision(obj), ""
        if mutate:
            mutate()
        obj2, _ = run_hook(r, dict(pre, hook_event_name="PostToolUse", tool_response={"stdout": ""}), event="post",
                           env_extra=env)
        return decision(obj), obj2.get("hookSpecificOutput", {}).get("additionalContext", "")

    def signed(path):
        os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
        try:
            importlib.reload(signing)
            return signing.verify(json.load(open(path))) is True
        finally:
            del os.environ["EVIDENCE_SIGNING_KEY"]

    # REQ-SLF-04: the hook performs `change start` / `change advance`, signed with the engine's key
    r = make_repo(branch="fix/ABC-9-thing")
    sp = os.path.join(r, ".evidence", "changes", "ABC-9", "state.json")
    (got, reason), note = pre_post(r, f"python3 {evidence} change start ABC-9 --tier 2 --kind fix", "l1", env=KEY)
    check("REQ-SLF-04 agent `change start` is performed by the hook and its state is signed",
          got == "deny" and "Done by the gate engine" in reason and "Started ABC-9" in reason
          and os.path.isfile(sp) and signed(sp) and note == "", (got, reason, note))
    os.makedirs(os.path.join(r, "intent", "x"), exist_ok=True)
    open(os.path.join(r, "intent", "x", "spec.md"), "w").write("# Spec\nTracker: ABC-9\n")
    (got, reason), _ = pre_post(r, f"cd {r} && evidence change advance ABC-9 plan", "l2", env=KEY)
    check("REQ-SLF-04 agent `change advance` is performed by the hook and stays signed",
          "Done by the gate engine" in reason and json.load(open(sp)).get("stage") == "plan" and signed(sp), reason)
    shutil.rmtree(r)
    r = make_repo(branch="fix/ABC-9-thing")
    sp = os.path.join(r, ".evidence", "changes", "ABC-9", "state.json")
    (got, reason), _ = pre_post(r, "git switch -c fix/ABC-9-x && evidence change start ABC-9 --tier 1 --kind fix", "l3", env=KEY)
    check("REQ-SLF-04 a lifecycle call chained with another program is denied and writes nothing",
          got == "deny" and "own command" in reason and not os.path.exists(sp), reason)
    (got, reason), _ = pre_post(r, "evidence change start ABC-9 --tier 2 --kind fix", "l4", env=NOORG)
    check("REQ-SLF-04 without a key, the hook refuses a Tier 2 start (unsigned-mode cap)",
          got == "deny" and "UNSIGNED MODE" in reason and not os.path.exists(sp), reason)
    pre = {"session_id": "s7", "cwd": r, "tool_name": "Bash", "permission_mode": "plan",
           "tool_input": {"command": "evidence change start ABC-9 --tier 1 --kind fix"}, "tool_use_id": "l4p"}
    got, reason = decision(run_hook(r, pre, env_extra=KEY)[0])
    check("REQ-SLF-04 in plan mode the hook performs nothing", got == "deny" and "Plan mode" in reason and not os.path.exists(sp), reason)
    (got, reason), _ = pre_post(r, "evidence change start ABC-9 --tier 1 --kind fix", "l5", env=NOORG)
    check("REQ-SLF-04 without a key, a Tier 1 start is performed", "Started ABC-9" in reason and os.path.isfile(sp), reason)
    shutil.rmtree(r)
    r = make_repo(branch="fix/ABC-9-thing")
    sp = os.path.join(r, ".evidence", "changes", "ABC-9", "state.json")
    fake = os.path.join(r, "evidence")
    open(fake, "w").write("import os\nos.makedirs('.evidence/changes/ABC-9', exist_ok=True)\n"
                          "open('.evidence/changes/ABC-9/state.json','w').write('{\"stage\": \"approved\"}')\n")
    (got, reason), _ = pre_post(r, "python3 ./evidence change start ABC-9 --tier 1 --kind fix", "l6", env=KEY)
    check("REQ-SLF-04 the hook runs its own engine, never the agent's ./evidence script",
          os.path.isfile(sp) and json.load(open(sp)).get("stage") == "plan" and signed(sp), reason)
    shutil.rmtree(r)
    # security review: the hook is unsandboxed, so what it writes and where it signs is constrained
    r = make_repo(branch="fix/ABC-9-thing")
    outside = os.path.realpath(tempfile.mkdtemp(prefix="evidence-outside-"))
    victim = os.path.join(r, ".claude", "settings.json")
    os.makedirs(os.path.dirname(victim))
    open(victim, "w").write("{}")
    for label, target in (("absolute path outside the repo", os.path.join(outside, "x.md")),
                          ("`..` escape", "../" + os.path.basename(outside) + "/y.md"),
                          ("control-plane file", ".claude/settings.json"), ("non-Markdown path", "src/app.py")):
        (got, reason), _ = pre_post(r, f"evidence change start ABC-9 --tier 1 --kind fix --quick 'x' --files src/app.py --plan '{target}'",
                                    "p-" + label[:6], env=KEY)
        check(f"REQ-SLF-04 security: --plan {label} is refused and nothing is written",
              got == "deny" and "Done by the gate engine" not in reason and not os.listdir(outside) and open(victim).read() == "{}"
              and open(os.path.join(r, "src", "app.py")).read() == "a = 1\n"
              and not os.path.exists(os.path.join(r, ".evidence", "changes", "ABC-9")), reason)
    os.makedirs(os.path.join(r, "plan"))
    open(os.path.join(r, "plan", "ABC-9.md"), "w").write("keep\n")
    human = {k: v for k, v in BASE_ENV.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    res = subprocess.run([sys.executable, evidence, "change", "start", "ABC-9", "--tier", "1", "--kind", "fix", "--quick", "x",
                          "--files", "src/app.py"], cwd=r, capture_output=True, text=True, env=human)
    check("REQ-SLF-04 security: --quick (human CLI) never overwrites an existing plan",
          res.returncode != 0 and open(os.path.join(r, "plan", "ABC-9.md")).read() == "keep\n", res.stdout + res.stderr)
    shutil.rmtree(os.path.join(r, "plan"))
    os.symlink(outside, os.path.join(r, "plan"))
    (got, reason), _ = pre_post(r, "evidence change start ABC-9 --tier 1 --kind fix --quick 'x' --files src/app.py", "p-ln", env=KEY)
    check("REQ-SLF-04 security: --quick will not follow a symlinked plan/ directory out of the repository",
          got == "deny" and "Done by the gate engine" not in reason and not os.listdir(outside), reason)
    os.remove(os.path.join(r, "plan"))
    other = make_repo(branch="fix/ABC-9-thing")
    (got, reason), _ = pre_post(r, f"cd {other} && evidence change start ABC-9 --tier 1 --kind fix", "p-cd", env=KEY)
    check("REQ-SLF-04 security: the hook will not start or sign a change in another repository",
          got == "deny" and "own repository" in reason and not os.path.exists(os.path.join(other, ".evidence")), reason)
    os.makedirs(os.path.join(r, ".evidence", "changes", "ABC-9"), exist_ok=True)
    forged = os.path.join(r, ".evidence", "changes", "ABC-9", "state.json")
    json.dump({"key": "ABC-9", "tier": 1, "kind": "fix", "stage": "spec", "fix_base": "deadbeef"}, open(forged, "w"))
    (got, reason), _ = pre_post(r, "evidence change advance ABC-9 plan", "p-adv", env=KEY)
    check("REQ-SLF-04 security: advance refuses to re-sign unsigned (agent-written) state",
          "refused" in reason and not signed(forged), reason)
    shutil.rmtree(r)
    shutil.rmtree(other)
    shutil.rmtree(outside)

    # REQ-SLF-03: a status change without a content change is not a write
    r = make_repo()
    start_change(r, claims=("src/app.py",))
    sh("git add -A && git commit -q -m 'ABC-1: c'", r)
    os.makedirs(os.path.join(r, "notes"))
    open(os.path.join(r, "notes", "draft.md"), "w").write("x\n")
    sh("git add notes/draft.md", r)
    _, note = pre_post(r, "git reset -q", "i1", session="s1", mutate=lambda: sh("git reset -q", r))
    check("REQ-SLF-03 unstaging a file (staged -> untracked directory) is not reported as a write", note == "", note)
    _, note = pre_post(r, "./vendor/tool", "i2", session="s1",
                       mutate=lambda: open(os.path.join(r, "notes", "new.py"), "w").write("x\n"))
    check("REQ-SLF-03 a new file inside an untracked directory is still judged", "notes/new.py" in note, note)
    shutil.rmtree(r)

    # REQ-SLF-02: the session audit log may be ahead of the index by what was appended after staging
    r = make_repo()
    start_change(r)
    log = os.path.join(r, ".evidence", "audit", "s1.jsonl")
    record_agent(r, "ABC-1", "evidence-sdlc:verifier")
    import uuid
    pre_post(r, "git add -A .evidence", "c-" + uuid.uuid4().hex, session="s1", mutate=lambda: sh("git add -A .evidence", r))
    t, i = bash("git commit -m 'ABC-1: x' -m 'Agent-Session: s1'")
    case("REQ-SLF-02 commit allowed when the audit log only gained the `git add` call's entry since staging", r, t, i, "allow")
    lines = open(log).read().splitlines(True)
    open(log, "w").write(lines[0].replace('"s1"', '"s9"', 1) + "".join(lines[1:]))
    case("REQ-SLF-02 commit denied when the staged audit log is not a prefix (altered)", r, t, i, "deny", rule_hint="git add")
    open(log, "w").write("".join(lines))
    for n in range(3):
        run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": f"ls {n}"}}, event="post")
    case("REQ-SLF-02 commit denied when the audit log is more than two entries ahead of the index", r, t, i, "deny",
         rule_hint="git add")
    sh("git add -A .evidence", r)
    sp = os.path.join(r, ".evidence", "changes", "ABC-1", "state.json")
    stj = json.load(open(sp)); stj["note"] = "later"; json.dump(stj, open(sp, "w"))
    case("REQ-SLF-02 state.json changed after staging still denies", r, t, i, "deny", rule_hint="state.json")
    shutil.rmtree(r)
    r = make_repo()
    start_change(r)
    record_agent(r, "ABC-1", "evidence-sdlc:verifier")
    sh("git add -A .evidence/changes", r)
    case("REQ-SLF-02 commit denied when the audit log was never staged", r, t, i, "deny", rule_hint="git add")
    shutil.rmtree(r)


def suite_audit_concurrency_and_hook_scope():
    """PILOT-57 revision 2: audit forks (REQ-SLF-07/08) and the narrowed hook path (REQ-SLF-09)."""
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import importlib
    import signing
    import state as st
    KEY = {"EVIDENCE_SIGNING_KEY": "k" * 40}

    # REQ-SLF-07: concurrent appends from separate processes do not fork the chain
    r = make_repo()
    engine = os.path.join(HERE, "..", "engine")
    code = f"import sys; sys.path.insert(0, {engine!r}); import state; state.audit_append({r!r}, 'c1', {{'event': 'x'}})"
    procs = [subprocess.Popen([sys.executable, "-c", code], env=BASE_ENV, stderr=subprocess.PIPE) for _ in range(20)]
    errs = [p.communicate()[1].decode() for p in procs]
    codes = [p.returncode for p in procs]
    warnings = []
    ok, problems = st.audit_verify(os.path.join(r, ".evidence", "audit", "c1.jsonl"), warnings)
    n = len(open(os.path.join(r, ".evidence", "audit", "c1.jsonl")).read().splitlines())
    aside = glob.glob(os.path.join(r, ".evidence", "audit", "*.unwritable-*"))
    check("REQ-SLF-07 20 concurrent audit appends on a fresh repository keep one unbroken chain: every entry, no fork, "
          "no false tamper recovery", ok and not warnings and n == 20 and not any(codes) and not aside,
          (problems, warnings, n, codes, aside, [e for e in errs if e][:2]))
    shutil.rmtree(r)

    # REQ-SLF-08: a sibling fork is a warning; deletion, alteration and a bad signature still fail
    def entry(prev, i, session="s1"):
        e = {"event": "x", "i": i, "prev": prev, "session": session}
        e["hash"] = st.entry_hash(e, prev)
        return signing.sign(e)

    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    importlib.reload(signing)
    try:
        a = entry("", 1)
        b = entry(a["hash"], 2)
        c = entry(a["hash"], 3)  # sibling of b: written concurrently from the same last hash
        d = entry(c["hash"], 4)
        d2 = dict(d); d2["i"] = 99  # altered
        forged = {k: v for k, v in entry(a["hash"], 5).items() if k != "sig"}
        forged["sig"] = "0" * 64  # hash-correct sibling, bad signature
        tmp = tempfile.mkdtemp(prefix="evidence-audit-")

        def verify(lines):
            p = os.path.join(tmp, "s1.jsonl")  # named for its session, as real logs are (REQ-IMH-11 checks it)
            open(p, "w").write("".join(json.dumps(e, sort_keys=True) + "\n" for e in lines))
            w = []
            ok, probs = st.audit_verify(p, w)
            return ok, probs, w

        ok, probs, w = verify([a, b, c, d])
        check("REQ-SLF-08 a concurrent sibling fork verifies, reported as a named warning", ok and any("fork" in x for x in w), (probs, w))
        ok, probs, w = verify([a, c, d][:1] + [d])
        check("REQ-SLF-08 a deleted entry still fails verification", not ok, (probs, w))
        ok, probs, w = verify([a, b, c, d2])
        check("REQ-SLF-08 an altered entry still fails verification", not ok, (probs, w))
        ok, probs, w = verify([a, b, forged])
        check("REQ-SLF-08 a forked sibling with a bad signature fails", not ok, (probs, w))
        ok, probs, w = verify([a, b, entry(b["hash"], 6), entry(a["hash"], 7)])
        check("REQ-SLF-08 an entry pointing further back than its sibling is a break, not a fork", not ok, (probs, w))
        ok, probs, w = verify([a, b, b, d])
        check("REQ-SLF-08 an entry duplicated right after itself is a break, not a fork", not ok, (probs, w))
        y1 = entry("", 1, session="s2")
        ok, probs, w = verify([a, y1, entry(y1["hash"], 2, session="s2")])
        check("REQ-SLF-08 another session's chain spliced in after the first entry is a break, not a fork", not ok, (probs, w))
        shutil.rmtree(tmp)
    finally:
        del os.environ["EVIDENCE_SIGNING_KEY"]
        importlib.reload(signing)

    # REQ-SLF-09: the hook-performed path is narrow
    def pre(r, cmd, env=None, agent_type=None, tid="n"):
        p = {"session_id": "s9", "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": tid,
             "permission_mode": "default"}
        if agent_type:
            p["agent_type"], p["agent_id"] = agent_type, "a1"
        return decision(run_hook(r, p, env_extra=env)[0])

    r = make_repo(branch="fix/ABC-9-thing")
    sp = os.path.join(r, ".evidence", "changes", "ABC-9", "state.json")
    env = dict(KEY, CLAUDE_PROJECT_DIR=r)
    for opt in ("--plan plan/x.md", "--spec intent/x/spec.md", "--intent intent/x/intent.md", "--quick 'x' --files src/app.py"):
        got, reason = pre(r, f"evidence change start ABC-9 --tier 1 --kind fix {opt}", env=env, tid="o" + opt[2:6])
        check(f"REQ-SLF-09 the hook refuses `{opt.split()[0]}` and writes nothing",
              got == "deny" and "Done by the gate engine" not in reason and not os.path.exists(sp)
              and not os.path.exists(os.path.join(r, "plan")), reason)
    other = make_repo(branch="fix/ABC-9-thing")
    got, reason = pre(r, "evidence change start ABC-9 --tier 1 --kind fix", env=dict(KEY, CLAUDE_PROJECT_DIR=other))
    check("REQ-SLF-09 the hook refuses when the repository is not the session's project (CLAUDE_PROJECT_DIR)",
          got == "deny" and "own repository" in reason and not os.path.exists(sp), reason)
    shutil.rmtree(other)
    got, reason = pre(r, "evidence change start ABC-9 --tier 1 --kind fix", env=env, agent_type="evidence-sdlc:security-reviewer")
    check("REQ-SLF-09 a read-only agent cannot have the hook change lifecycle state", got == "deny" and not os.path.exists(sp), reason)
    got, reason = pre(r, "evidence change start ABC-9 --tier 1 --kind fix", env=env, tid="ok")
    hist = json.load(open(sp)).get("history", [{}]) if os.path.isfile(sp) else [{}]
    check("REQ-SLF-09 a hook-performed start records via: hook and the agent session",
          "Done by the gate engine" in reason and hist[-1].get("via") == "hook" and hist[-1].get("session") == "s9", (reason, hist))
    shutil.rmtree(r)

    # the KEY is a path component: absolute, `..` and slash keys are refused, and another repo's state is untouched
    human = {k: v for k, v in BASE_ENV.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    evidence = os.path.realpath(os.path.join(HERE, "..", "..", "bin", "evidence"))
    r = make_repo(branch="fix/ABC-9-thing")
    other = make_repo(branch="fix/ABC-3-x")
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    importlib.reload(signing)
    st.save_state(other, "ABC-3", {"key": "ABC-3", "tier": 1, "kind": "fix", "stage": "verified"})
    del os.environ["EVIDENCE_SIGNING_KEY"]
    importlib.reload(signing)
    osp = os.path.join(other, ".evidence", "changes", "ABC-3", "state.json")
    before = open(osp).read()
    rel_other = os.path.relpath(os.path.join(other, ".evidence", "changes", "ABC-3"), os.path.join(r, ".evidence", "changes"))
    for label, k in (("absolute", os.path.join(other, ".evidence", "changes", "ABC-3")), ("`..`", rel_other), ("slash", "ABC-3/x")):
        got, reason = pre(r, f"evidence change advance {k} plan", env=KEY, tid="k" + label[:3])
        check(f"REQ-SLF-09 an {label} change key is refused by the hook and another repository's state is untouched",
              got == "deny" and "Done by the gate engine" not in reason and open(osp).read() == before, reason)
    res = subprocess.run([sys.executable, evidence, "change", "advance", os.path.join(other, ".evidence", "changes", "ABC-3"), "plan"],
                         cwd=r, capture_output=True, text=True, env=human)
    check("REQ-SLF-09 the CLI refuses a path as a change key for every subcommand", res.returncode != 0 and open(osp).read() == before,
          res.stdout + res.stderr)
    os.makedirs(os.path.join(r, ".evidence", "changes", "ABC-9"))
    shutil.copy(osp, os.path.join(r, ".evidence", "changes", "ABC-9", "state.json"))
    try:
        st.load_state(r, "ABC-9")
        loaded = True
    except ValueError:
        loaded = False
    check("REQ-SLF-09 a signed state copied under another key's directory is rejected on load", not loaded)
    got, reason = pre(r, "evidence change start ABC-8 --tier 1 --kind fix", env=dict(KEY, CLAUDE_PROJECT_DIR=None), tid="nopd")
    check("REQ-SLF-09 without CLAUDE_PROJECT_DIR the hook performs nothing (fails closed)",
          got == "deny" and not os.path.exists(os.path.join(r, ".evidence", "changes", "ABC-8")), reason)
    shutil.rmtree(r)
    shutil.rmtree(other)

    # N1: engine writes never follow a symlink or a hard link planted by the agent's shell
    r = make_repo(branch="fix/ABC-9-thing")
    outside = os.path.realpath(tempfile.mkdtemp(prefix="evidence-outside-"))
    os.makedirs(os.path.join(r, ".evidence", "changes"))
    os.symlink(outside, os.path.join(r, ".evidence", "changes", "ABC-9"))
    got, reason = pre(r, "evidence change start ABC-9 --tier 1 --kind fix", env=KEY, tid="sl1")
    check("REQ-SLF-09 security: a symlinked change directory does not redirect the hook's signed write",
          "Done by the gate engine" not in reason and "own repository" not in reason and not os.listdir(outside), reason)
    os.remove(os.path.join(r, ".evidence", "changes", "ABC-9"))
    victim = os.path.join(outside, "victim.txt")
    open(victim, "w").write("keep\n")
    os.makedirs(os.path.join(r, ".evidence", "audit"), exist_ok=True)
    os.symlink(victim, os.path.join(r, ".evidence", "audit", "s8.jsonl"))
    run_hook(r, {"session_id": "s8", "cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "README.md"}}, event="post")
    check("REQ-SLF-09 security: the audit append does not follow a symlinked log", open(victim).read() == "keep\n")
    os.remove(os.path.join(r, ".evidence", "audit", "s8.jsonl"))
    os.link(victim, os.path.join(r, ".evidence", "audit", "s8.jsonl"))
    run_hook(r, {"session_id": "s8", "cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "README.md"}}, event="post")
    check("REQ-SLF-09 security: the audit append refuses a hard-linked log", open(victim).read() == "keep\n")
    os.remove(os.path.join(r, ".evidence", "audit", "s8.jsonl"))
    got, reason = pre(r, "evidence change start ABC-9 --tier 1 --kind fix", env=KEY, tid="sl2")
    sp9 = os.path.join(r, ".evidence", "changes", "ABC-9", "state.json")
    os.remove(sp9)
    os.link(victim, sp9)
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    importlib.reload(signing)
    st.save_state(r, "ABC-9", {"key": "ABC-9", "tier": 1, "kind": "fix", "stage": "plan"})
    del os.environ["EVIDENCE_SIGNING_KEY"]
    importlib.reload(signing)
    check("REQ-SLF-09 security: saving state replaces a hard-linked state.json instead of writing through it",
          open(victim).read() == "keep\n" and json.load(open(sp9)).get("stage") == "plan")
    shutil.rmtree(r)
    shutil.rmtree(outside)

    # N2: an unreadable change state does not swallow the violations the monitor found
    r = make_repo()
    start_change(r, claims=("src/app.py",))
    sh("git add -A && git commit -q -m 'ABC-1: c'", r)
    p = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"}, "tool_use_id": "n2",
         "permission_mode": "default"}
    run_hook(r, p)
    open(os.path.join(r, "src", "sneaky.py"), "w").write("x\n")
    open(os.path.join(r, ".evidence", "changes", "ABC-1", "state.json"), "w").write("{not json")
    run_hook(r, dict(p, hook_event_name="PostToolUse"), event="post")
    vfiles = glob.glob(os.path.join(r, ".evidence", "violations", "*")) + glob.glob(os.path.join(r, ".evidence", "changes", "*", "violations.json"))
    log = open(os.path.join(r, ".evidence", "audit", "s1.jsonl")).read()
    check("REQ-SLF-09 an unreadable change state still records the monitor's violations and an engine-error entry",
          any("sneaky.py" in open(f).read() for f in vfiles) and "engine-error" in log and "integrity-violation" in log, (vfiles, log[-400:]))
    shutil.rmtree(r)

    # N3: the tolerated unstaged tail may hold only this session's `tool` entries, never a deny
    r = make_repo()
    start_change(r)
    record_agent(r, "ABC-1", "evidence-sdlc:verifier")
    sh("git add -A .evidence", r)
    st.audit_append(r, "s1", {"event": "deny", "rule": "x", "tool": "Bash"})
    t, i = bash("git commit -m 'ABC-1: x' -m 'Agent-Session: s1'")
    case("REQ-SLF-02 a deny entry left out of the staged audit log blocks the commit", r, t, i, "deny", rule_hint="git add")
    shutil.rmtree(r)

    # F3: a log the engine cannot append to is moved aside, a fresh log records it, and a violation is opened
    r = make_repo()
    start_change(r, claims=("src/app.py",))
    outside = os.path.realpath(tempfile.mkdtemp(prefix="evidence-outside-"))
    log = os.path.join(r, ".evidence", "audit", "s6.jsonl")
    st.audit_append(r, "s6", {"event": "tool"})
    os.link(log, os.path.join(outside, "copy.jsonl"))
    before = open(os.path.join(outside, "copy.jsonl")).read()
    run_hook(r, {"session_id": "s6", "cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "README.md"}}, event="post")
    first = json.loads(open(log).read().splitlines()[0])
    vtext = "".join(open(f).read() for f in glob.glob(os.path.join(r, ".evidence", "violations", "*")))
    check("REQ-SLF-07 security: a hard-linked audit log is moved aside, a fresh log records it, and a violation is opened",
          first.get("event") == "audit-log-replaced" and glob.glob(log + ".unwritable-*") and "audit-tamper" in vtext
          and open(os.path.join(outside, "copy.jsonl")).read() == before, (first, vtext))
    os.chmod(log, 0o444)
    run_hook(r, {"session_id": "s6", "cwd": r, "tool_name": "Edit", "tool_input": {"file_path": "README.md"}}, event="post")
    check("REQ-SLF-07 security: a read-only audit log is moved aside the same way",
          json.loads(open(log).read().splitlines()[0]).get("event") == "audit-log-replaced"
          and len(glob.glob(log + ".unwritable-*")) == 2)
    adir = os.path.join(r, ".evidence", "audit")
    os.chmod(log, 0o000)
    os.chmod(adir, 0o555)
    try:
        got, reason = decision(run_hook(r, {"session_id": "s6", "cwd": r, "hook_event_name": "PreToolUse", "tool_name": "Read",
                                            "tool_input": {"file_path": "README.md"}, "permission_mode": "default"})[0])
    finally:
        os.chmod(adir, 0o755)
        os.chmod(log, 0o644)
    check("REQ-SLF-07 security: when the audit log cannot be written at all, every call is denied", got == "deny"
          and "audit log cannot be written" in reason, reason)
    readp = {"session_id": "s5", "cwd": r, "hook_event_name": "PreToolUse", "tool_name": "Read",
             "tool_input": {"file_path": "README.md"}, "permission_mode": "default"}
    os.chmod(adir, 0o000)
    try:
        got, reason = decision(run_hook(r, readp)[0])
    finally:
        os.chmod(adir, 0o755)
    check("REQ-SLF-07 security: an unreadable audit directory (the log itself not yet seen) denies every call",
          got == "deny" and "audit log cannot be written" in reason, reason)
    os.chmod(adir, 0o555)
    try:
        got, reason = decision(run_hook(r, dict(readp, session_id="fresh1"))[0])
    finally:
        os.chmod(adir, 0o755)
    check("REQ-SLF-07 security: a read-only audit directory denies a new session whose log cannot be created",
          got == "deny" and "audit log cannot be written" in reason
          and not os.path.exists(os.path.join(adir, "fresh1.jsonl")), reason)
    shutil.move(adir, adir + ".real")
    open(adir, "w").write("not a directory\n")
    got, reason = decision(run_hook(r, readp)[0])
    os.remove(adir)
    shutil.move(adir + ".real", adir)
    check("REQ-SLF-07 security: an audit directory replaced by a file denies every call",
          got == "deny" and "audit log cannot be written" in reason, reason)
    shutil.rmtree(r)
    shutil.rmtree(outside)

    # F5: an entry edited in place (deny -> tool, same length) does not pass as the tolerated tail
    r = make_repo()
    start_change(r)
    record_agent(r, "ABC-1", "evidence-sdlc:verifier")
    sh("git add -A .evidence", r)
    st.audit_append(r, "s1", {"event": "deny", "rule": "x", "tool": "Bash"})
    lp = os.path.join(r, ".evidence", "audit", "s1.jsonl")
    text = open(lp).read()
    open(lp, "w").write(text[: text.rstrip("\n").rfind("\n") + 1] + text[text.rstrip("\n").rfind("\n") + 1:].replace('"event": "deny"', '"event": "tool"'))
    t, i = bash("git commit -m 'ABC-1: x' -m 'Agent-Session: s1'")
    case("REQ-SLF-02 a deny entry rewritten in place as a `tool` entry does not pass as the unstaged tail", r, t, i, "deny",
         rule_hint="git add")
    shutil.rmtree(r)

    # F2: an integrity check the agent makes fail is recorded, not swallowed
    r = make_repo()
    start_change(r, claims=("src/app.py",))
    sh("git add -A && git commit -q -m 'ABC-1: c'", r)
    p = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"}, "tool_use_id": "f2",
         "permission_mode": "default"}
    run_hook(r, p, env_extra=KEY)
    bang = os.path.join(r, "!")
    os.makedirs(bang)
    open(os.path.join(bang, "managed-settings.json"), "w").write("{}")
    os.chmod(bang, 0o555)
    try:
        obj, _ = run_hook(r, dict(p, hook_event_name="PostToolUse"), event="post", env_extra=KEY)
    finally:
        os.chmod(bang, 0o755)
    note = obj.get("hookSpecificOutput", {}).get("additionalContext", "")
    vtext = json.dumps([open(f).read() for f in glob.glob(os.path.join(r, ".evidence", "**", "violations*"), recursive=True)])
    # Since PILOT-58 (REQ-IMH-01) a refused removal is its own violation instead of an exception
    # that fails the whole check; either way it must be recorded, never swallowed.
    check("REQ-SLF-09 security: a failing integrity check is recorded as a violation, not swallowed",
          ("integrity check for that command failed" in note and "integrity-check-error" in vtext)
          or ("could not be removed safely" in note and "control-plane-removal-refused" in vtext), (note, vtext))
    shutil.rmtree(r)

    # the human CLI's artifact-path check is case-insensitive (macOS/Windows filesystems)
    r = make_repo(branch="fix/ABC-9-thing")
    for p in (".Claude/commands/x.md", ".EVIDENCE/x.md", ".Git/x.md"):
        res = subprocess.run([sys.executable, evidence, "change", "start", "ABC-9", "--tier", "1", "--kind", "fix", "--plan", p],
                             cwd=r, capture_output=True, text=True, env=human)
        check(f"REQ-SLF-09 `--plan {p}` is refused whatever its case", res.returncode != 0 and not os.path.exists(sp), res.stdout + res.stderr)
    shutil.rmtree(r)


def suite_pilot58():
    """PILOT-58: integrity-monitor and engine git hardening (spec REQ-IMH-01..24, local set)."""
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import importlib
    import state as st
    KEY = {"EVIDENCE_SIGNING_KEY": "k" * 40}
    import uuid

    def around(r, mutate, env=None, cmd="./vendor/tool", session="s1"):
        tid = "p58-" + uuid.uuid4().hex[:8]
        p = {"session_id": session, "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": tid,
             "permission_mode": "default"}
        pre = decision(run_hook(r, p, env_extra=env)[0])
        if pre[0] == "deny":
            return pre, ""
        mutate()
        obj, _ = run_hook(r, dict(p, hook_event_name="PostToolUse", tool_response={"stdout": ""}), event="post", env_extra=env)
        return pre, obj.get("hookSpecificOutput", {}).get("additionalContext", "")

    def vtext(r):
        return json.dumps([open(f).read() for f in glob.glob(os.path.join(r, ".evidence", "**", "violations*"), recursive=True)
                           if os.path.isfile(f)])

    def committed_repo(claims=("src/app.py",)):
        r = make_repo()
        start_change(r, claims=claims)
        sh("git add -A && git commit -q -m 'ABC-1: c'", r)
        return r

    # REQ-IMH-01: removal/restore never goes through a symlink or outside the repository
    r = committed_repo()
    outside = os.path.realpath(tempfile.mkdtemp(prefix="evidence-outside-"))
    open(os.path.join(outside, "keep.txt"), "w").write("keep\n")
    os.makedirs(os.path.join(r, ".evidence", "violations"), exist_ok=True)
    _, note = around(r, lambda: os.symlink(outside, os.path.join(r, ".evidence", "violations", "x")), env=KEY)
    check("REQ-IMH-01 a symlinked control-plane directory is reported, and nothing outside the repository is removed",
          os.path.isfile(os.path.join(outside, "keep.txt")) and "symlink" in note.lower(), note)
    if os.path.lexists(os.path.join(r, ".evidence", "violations", "x")):
        os.remove(os.path.join(r, ".evidence", "violations", "x"))
    shutil.rmtree(outside)
    shutil.rmtree(r)
    for label, rel, is_dir in (("a symlinked change directory", (".evidence", "changes", "ZZZ-9"), True),
                               ("a symlinked audit log", (".evidence", "audit", "evil.jsonl"), False)):
        r = committed_repo()
        st.audit_append(r, "s1", {"event": "x"})
        outside = os.path.realpath(tempfile.mkdtemp(prefix="evidence-outside-"))
        target = outside if is_dir else os.path.join(outside, "log.jsonl")
        keep = os.path.join(outside, "keep.txt") if is_dir else target
        open(keep, "w").write("keep\n")
        link = os.path.join(r, *rel)
        _, note = around(r, lambda: os.symlink(target, link), env=KEY)
        check(f"REQ-IMH-01 {label} is reported, and its target outside the repository is untouched",
              os.path.isfile(keep) and open(keep).read() == "keep\n" and "symlink" in note.lower(), note)
        if os.path.lexists(link):
            os.remove(link)
        shutil.rmtree(outside)
        shutil.rmtree(r)

    # REQ-IMH-02: a non-file at a violations path is an open violation
    r = committed_repo()
    os.makedirs(os.path.join(r, ".evidence", "changes", "ABC-1", "violations.json"))
    record_agent(r, "ABC-1", "evidence-sdlc:verifier")
    t, i = bash("git push -u origin feature/ABC-1-login")
    case("REQ-IMH-02 a directory at a violations-record path keeps push closed", r, t, i, "deny", rule_hint="violation")
    shutil.rmtree(r)

    # REQ-IMH-05: .evidence directory mode/identity changes are violations
    r = committed_repo()
    st.audit_append(r, "s1", {"event": "x"})
    adir = os.path.join(r, ".evidence", "audit")
    _, note = around(r, lambda: os.chmod(adir, 0o555))
    os.chmod(adir, 0o755)
    check("REQ-IMH-05 a chmod of .evidence/audit during a call is a violation", ".evidence/audit" in note, note)
    _, note = around(r, lambda: (os.rename(adir, adir + ".old"), shutil.copytree(adir + ".old", adir)))
    check("REQ-IMH-05 a swapped .evidence/audit directory is a violation", ".evidence/audit" in note, note)
    shutil.rmtree(r)

    # REQ-IMH-06: an unwritable post-call audit entry records a violation
    r = committed_repo()
    st.audit_append(r, "s1", {"event": "x"})
    adir6 = os.path.join(r, ".evidence", "audit")
    log6 = os.path.join(adir6, "s1.jsonl")

    def lock_audit():
        os.chmod(log6, 0o444)
        os.chmod(adir6, 0o555)
    try:
        around(r, lock_audit)
        v = vtext(r)
    finally:
        os.chmod(adir6, 0o755)
        os.chmod(log6, 0o644)
    check("REQ-IMH-06 an unwritable post-call audit entry is recorded as an audit-unwritable violation", "audit-unwritable" in v, v)
    got, reason = decision(run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"},
                                        "tool_use_id": "p58-after6", "permission_mode": "default"})[0])
    check("REQ-IMH-06 the next call after an unwritable audit entry is denied", got == "deny", reason[:200])
    shutil.rmtree(r)

    # REQ-IMH-07: deleting a file inside an untracked directory is judged
    r = committed_repo()
    os.makedirs(os.path.join(r, "notes"))
    open(os.path.join(r, "notes", "a.py"), "w").write("x = 1\n")  # gated (a .txt would be ungated) and unclaimed
    _, note = around(r, lambda: os.remove(os.path.join(r, "notes", "a.py")))
    check("REQ-IMH-07 deleting an unclaimed untracked file is judged like any delete", "notes/a.py" in note, note)
    shutil.rmtree(r)

    # REQ-IMH-08: a snapshot replaced by a link to a large file is treated as altered; post completes
    r = committed_repo()
    import integrity
    bigdir = tempfile.mkdtemp(prefix="evidence-big-")
    big = os.path.join(bigdir, "big")
    with open(big, "wb") as f:
        f.truncate(64 * 1024 * 1024)
    tid = "p58-snap-" + uuid.uuid4().hex[:6]
    p = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"}, "tool_use_id": tid,
         "permission_mode": "default"}
    run_hook(r, p)
    sp = integrity._snap_path("s1", tid)
    if os.path.lexists(sp):
        os.remove(sp)
    os.symlink(big, sp)
    obj, err = run_hook(r, dict(p, hook_event_name="PostToolUse"), event="post")
    note = obj.get("hookSpecificOutput", {}).get("additionalContext", "")
    check("REQ-IMH-08 a snapshot replaced by a symlink is a violation and post completes",
          "snapshot" in note.lower() and "Traceback" not in err, (note, err[-300:]))
    if os.path.lexists(sp):
        os.remove(sp)
    shutil.rmtree(bigdir)
    shutil.rmtree(r)

    # REQ-IMH-09: command-executing repository config is refused; a marker script never runs
    def git_cfg_case(label, setup, env=None, expect_deny=True):
        """`setup(r, script)` plants `script` where git might run it; it must never run. Config the engine reads
        is refused (deny); config from the environment is scrubbed instead (expect_deny=False)."""
        r = committed_repo()
        marker = os.path.join(r, "MARKER")
        script = os.path.join(r, "mk.sh")
        open(script, "w").write(f"#!/bin/sh\ntouch {marker}\ncat\n")
        os.chmod(script, 0o755)
        got = setup(r, script)
        env = got if isinstance(got, dict) else env
        # something dirty and tracked, so a diff or status has content to process
        open(os.path.join(r, "src", "app.py"), "a").write("b = 2\n")
        tid = "p58-g-" + uuid.uuid4().hex[:6]
        p = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_use_id": tid,
             "permission_mode": "default"}
        got, reason = decision(run_hook(r, p, env_extra=env)[0])
        run_hook(r, dict(p, hook_event_name="PostToolUse"), event="post", env_extra=env)
        check(f"REQ-IMH-09 {label}: {'refused and ' if expect_deny else ''}the marker never runs",
              (got == "deny" or not expect_deny) and not os.path.exists(marker), (got, reason[:200], os.path.exists(marker)))
        shutil.rmtree(r, ignore_errors=True)

    def cfg(r, *kv):
        for k, v in kv:
            sh(f"git config {k} '{v}'", r)
    git_cfg_case("core.fsmonitor", lambda r, s: cfg(r, ("core.fsmonitor", s)))
    git_cfg_case("diff driver command + .gitattributes",
                 lambda r, s: (cfg(r, ("diff.evil.command", s)), open(os.path.join(r, ".gitattributes"), "w").write("*.py diff=evil\n")))
    git_cfg_case("textconv", lambda r, s: cfg(r, ("diff.evil.textconv", s)))
    git_cfg_case("info/attributes filter",
                 lambda r, s: (cfg(r, ("filter.evil.clean", s)),
                               open(os.path.join(r, ".git", "info", "attributes"), "w").write("* filter=evil\n")))
    git_cfg_case("core.attributesFile", lambda r, s: cfg(r, ("core.attributesFile", s)))
    git_cfg_case("filter.lfs.clean with an embedded newline",
                 lambda r, s: open(os.path.join(r, ".git", "config"), "a").write(
                     f'[filter "lfs"]\n\tclean = "git-lfs clean -- %f\\n{s}"\n'))

    def include_case(r, s):
        inc = os.path.join(r, "evil.inc")
        open(inc, "w").write(f"[core]\n\tfsmonitor = {s}\n")
        cfg(r, ("include.path", inc))
    git_cfg_case("config via include.path", include_case)

    def include_if_case(r, s):
        inc = os.path.join(r, "evil.inc")
        open(inc, "w").write(f"[core]\n\tfsmonitor = {s}\n")
        cfg(r, ("includeIf.onbranch:feature/**.path", inc))
    git_cfg_case("config via includeIf", include_if_case)

    def worktree_cfg(r, s):
        cfg(r, ("extensions.worktreeConfig", "true"))
        open(os.path.join(r, ".git", "config.worktree"), "w").write(f"[core]\n\tfsmonitor = {s}\n")
    git_cfg_case("config.worktree", worktree_cfg)

    def gitfile(r, s):
        real = os.path.realpath(tempfile.mkdtemp(prefix="evidence-gitdir-"))
        os.rmdir(real)
        shutil.move(os.path.join(r, ".git"), real)
        open(os.path.join(r, ".git"), "w").write(f"gitdir: {real}\n")
        sh(f"git config core.fsmonitor '{s}'", r)
    git_cfg_case("a .git file pointing at a git dir with command config", gitfile)

    def submodule(r, s):
        sub = os.path.realpath(tempfile.mkdtemp(prefix="evidence-sub-"))
        sh("git init -q -b main && echo a > f && git add f && git commit -q -m init", sub)
        sh(f"git -c protocol.file.allow=always submodule -q add {sub} sub && git commit -q -m 'ABC-1: sub'", r)
        sh(f"git config filter.evil.clean '{s}' && a=$(git rev-parse --git-path info/attributes) && mkdir -p \"$(dirname \"$a\")\" "
           f"&& echo '* filter=evil' > \"$a\" && echo b >> f", os.path.join(r, "sub"))
        sh(f"git config core.fsmonitor '{s}'", os.path.join(r, "sub"))
    git_cfg_case("a submodule's filter and fsmonitor", submodule, expect_deny=False)
    git_cfg_case("an inherited GIT_CONFIG_PARAMETERS", lambda r, s: {"GIT_CONFIG_PARAMETERS": f"'core.fsmonitor'='{s}'"},
                 expect_deny=False)
    git_cfg_case("an inherited GIT_EXTERNAL_DIFF", lambda r, s: {"GIT_EXTERNAL_DIFF": s}, expect_deny=False)

    # a git child process gets the neutralising flags and no key in its environment
    r = committed_repo()
    seen = []
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    try:
        importlib.reload(st)
        real_run = st.subprocess.run

        def spy(argv, *a, **k):
            seen.append((list(argv), k.get("env")))
            return real_run(argv, *a, **k)
        st.subprocess.run = spy
        try:
            if hasattr(st, "run_git"):
                st.run_git(["status", "--porcelain"], r)
        finally:
            st.subprocess.run = real_run
    finally:
        del os.environ["EVIDENCE_SIGNING_KEY"]
    gitcalls = [(a, e) for a, e in seen if a and os.path.basename(a[0]) == "git"]
    check("REQ-IMH-09 run_git starts git with core.fsmonitor=false and core.hooksPath=/dev/null, and without the key",
          gitcalls and all("core.fsmonitor=false" in a and "core.hooksPath=/dev/null" in a and e is not None
                           and "EVIDENCE_SIGNING_KEY" not in e for a, e in gitcalls),
          [(a[:8], None if e is None else "EVIDENCE_SIGNING_KEY" in e) for a, e in gitcalls] or "run_git missing")
    shutil.rmtree(r)
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    os.environ["GIT_CONFIG_PARAMETERS"] = "'core.fsmonitor'='/bin/false'"
    try:
        importlib.reload(st)
        child = st._child_env() if hasattr(st, "_child_env") else dict(os.environ)
    finally:
        del os.environ["EVIDENCE_SIGNING_KEY"]
        del os.environ["GIT_CONFIG_PARAMETERS"]
    check("REQ-IMH-09 engine child processes never inherit EVIDENCE_SIGNING_KEY or GIT_* variables",
          "EVIDENCE_SIGNING_KEY" not in child and not any(k.startswith("GIT_") and k not in ("GIT_CONFIG_NOSYSTEM", "GIT_ATTR_SOURCE")
                                                          for k in child),
          sorted(k for k in child if k.startswith("GIT_") or k == "EVIDENCE_SIGNING_KEY"))
    r = committed_repo()
    home = tempfile.mkdtemp(prefix="evidence-home-")
    open(os.path.join(home, ".gitconfig"), "w").write("[credential]\n\thelper = osxkeychain\n")
    got, reason = decision(run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "ls"},
                                        "tool_use_id": "p58-cred", "permission_mode": "default"}, env_extra={"HOME": home})[0])
    check("REQ-IMH-09 a global credential.helper is accepted", got == "allow", reason)
    sh("git config credential.helper store", r)
    got, reason = decision(run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "ls"},
                                        "tool_use_id": "p58-cred2", "permission_mode": "default"}, env_extra={"HOME": home})[0])
    check("REQ-IMH-09 a local credential.helper is refused", got == "deny" and "credential" in reason, reason)
    shutil.rmtree(home)
    shutil.rmtree(r)

    # REQ-IMH-23: git failing mid-call fails closed, and the control plane is still restored
    r = committed_repo()
    cp = os.path.join(r, ".evidence", "changes", "ABC-1", "approval.json")
    before = open(cp).read()
    cfgp = os.path.join(r, ".git", "config")
    good_cfg = open(cfgp).read()

    def break_git():
        open(cfgp, "a").write("[\n")
        os.remove(cp)
    _, note = around(r, break_git, env=KEY)
    restored = os.path.isfile(cp) and open(cp).read() == before
    got, reason = decision(run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "ls"},
                                        "tool_use_id": "p58-gu", "permission_mode": "default"}, env_extra=KEY)[0])
    check("REQ-IMH-23 git failing mid-call is a violation, the control plane is still restored, and the next call is denied",
          "git-unavailable" in (note + vtext(r)) and restored and got == "deny", (note[:200], restored, got, reason[:200]))
    open(cfgp, "w").write(good_cfg)
    shutil.rmtree(r)

    # REQ-IMH-24: gh is pinned to --repo and runs without the key or GIT_*
    r = committed_repo()
    ghlog = os.path.join(r, "gh.log")
    fake = os.path.join(r, "fake-gh")
    open(fake, "w").write(f"#!/bin/sh\necho \"ARGS $@\" > {ghlog}\nenv >> {ghlog}\necho '{{}}'\n")
    os.chmod(fake, 0o755)
    os.environ.update({"EVIDENCE_GH": fake, "EVIDENCE_SIGNING_KEY": "k" * 40, "GIT_DIR": "/nonexistent"})
    ran, out, refused = False, "", False
    try:
        importlib.reload(st)
        if hasattr(st, "run_gh"):
            try:
                st.run_gh(["pr", "view", "1"], r, repo="o/r")
                ran = True
            except Exception as e:
                ran = repr(e)
            out = open(ghlog).read() if os.path.isfile(ghlog) else ""
            try:
                st.run_gh(["pr", "view", "1"], r, repo="")
            except Exception:
                refused = True
    finally:
        for k in ("EVIDENCE_GH", "EVIDENCE_SIGNING_KEY", "GIT_DIR"):
            os.environ.pop(k, None)
    check("REQ-IMH-24 gh gets --repo, and neither the key nor GIT_* reaches it; an empty repo is refused",
          ran is True and "--repo o/r" in out and "EVIDENCE_SIGNING_KEY" not in out and "GIT_DIR" not in out and refused,
          (ran, out[:200], refused))
    shutil.rmtree(r)

    # REQ-IMH-10: commit forms that bypass the index check are denied
    r = committed_repo()
    tr = " -m 'Agent-Session: s1'"
    open(os.path.join(r, "src", "app.py"), "a").write("c = 3\n")
    sh("git add src/app.py", r)
    run_hook(r, {"session_id": "s1", "cwd": r, "hook_event_name": "PreToolUse", "tool_name": "Bash",
                 "tool_input": {"command": "ls"}, "permission_mode": "default"})  # opens the session's audit log
    sh("git add -A .evidence", r)
    t, i = bash("git commit -m 'ABC-1: x'" + tr)
    case("REQ-IMH-10 control: a plain commit of the staged index is allowed", r, t, i, "allow")
    for c in ("git commit -m 'ABC-1: x'" + tr + " -- src/app.py", "git commit --only -m 'ABC-1: x'" + tr,
              "git commit -i -m 'ABC-1: x'" + tr, "git commit -p -m 'ABC-1: x'" + tr,
              "git commit --pathspec-from-file=list.txt -m 'ABC-1: x'" + tr,
              "git add src/app.py && git commit -m 'ABC-1: x'" + tr,
              "GIT_INDEX_FILE=/tmp/idx git commit -m 'ABC-1: x'" + tr,
              # abbreviated long options, which git accepts (security review, step 11)
              "git commit --patc -m 'ABC-1: x'" + tr, "git commit --inter -m 'ABC-1: x'" + tr,
              "git commit --pathspec-from-f=list.txt -m 'ABC-1: x'" + tr, "git commit --onl -m 'ABC-1: x'" + tr):
        t, i = bash(c)
        sh("git add -A .evidence", r)  # evidence staged, so only the bypass itself can deny
        case(f"REQ-IMH-10 commit bypass denied: {c[:60]}", r, t, i, "deny")
    shutil.rmtree(r)

    # REQ-IMH-11: replayed and cross-session audit entries break verification
    tmp = tempfile.mkdtemp(prefix="evidence-audit-")

    def entry(prev, i, session="s1"):
        e = {"event": "x", "i": i, "prev": prev, "session": session}
        e["hash"] = st.entry_hash(e, prev)
        return e
    a = entry("", 1)
    b = entry(a["hash"], 2)
    b2 = entry(a["hash"], 3)
    ap = os.path.join(tmp, "s1.jsonl")
    open(ap, "w").write("".join(json.dumps(e) + "\n" for e in (a, b, b2, b)))
    check("REQ-IMH-11 a replayed audit entry breaks verification", not st.audit_verify(ap, [])[0])
    open(ap, "w").write(json.dumps(entry("", 1, session="s2")) + "\n")
    check("REQ-IMH-11 an entry from another session breaks verification", not st.audit_verify(ap, [])[0])
    shutil.rmtree(tmp)

    # REQ-IMH-20: the audit-log prefix hash catches same-length rewrites
    r = committed_repo()
    for n in range(3):
        st.audit_append(r, "s1", {"event": "tool", "n": n})
    lp = os.path.join(r, ".evidence", "audit", "s1.jsonl")

    def rewrite():
        t = open(lp).read()
        open(lp, "w").write(t.replace('"n": 0', '"n": 9', 1))
    _, note = around(r, rewrite)
    check("REQ-IMH-20 a same-length rewrite of an earlier audit entry is a violation", "s1.jsonl" in note, note)
    shutil.rmtree(r)
    r = committed_repo()
    for n in range(3):
        st.audit_append(r, "s1", {"event": "tool", "n": n})
        st.audit_append(r, "s2", {"event": "tool", "n": n, "pad": "x" * 5})
    lp1, lp2 = (os.path.join(r, ".evidence", "audit", f"{s}.jsonl") for s in ("s1", "s2"))
    _, note = around(r, lambda: shutil.copyfile(lp2, lp1), session="s3")
    check("REQ-IMH-20 an audit log replaced by another session's log is a violation", "s1.jsonl" in note, note)
    shutil.rmtree(r)
    r = committed_repo()
    forged = os.path.join(r, ".evidence", "audit", "s9.jsonl")
    _, note = around(r, lambda: open(forged, "w").write(json.dumps({"event": "agent-completed", "session": "s9",
                                                                    "prev": "", "hash": "0" * 64}) + "\n"))
    check("REQ-IMH-20 an audit log created during the call must verify", "s9.jsonl" in note, note)
    shutil.rmtree(r)

    # Checkpoint security review (step 5) fixes
    # A3: git-lfs extension commands are refused; the exact allow-listed lfs filter alone passes
    git_cfg_case("lfs.extension clean command", lambda r, s: cfg(r, ("lfs.extension.x.clean", s)))
    r = committed_repo()
    for k, v in (("filter.lfs.clean", "git-lfs clean -- %f"), ("filter.lfs.smudge", "git-lfs smudge -- %f"),
                 ("filter.lfs.process", "git-lfs filter-process"), ("filter.lfs.required", "true")):
        sh(f"git config {k} '{v}'", r)
    got, reason = decision(run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "ls"},
                                        "tool_use_id": "p58-lfs", "permission_mode": "default"})[0])
    check("REQ-IMH-09 the exact allow-listed git-lfs filter values pass", got == "allow", reason)
    shutil.rmtree(r)

    # A1: an audit log too large to hash in time is refused by lstat alone, quickly
    r = committed_repo()
    import time
    os.makedirs(os.path.join(r, ".evidence", "audit"), exist_ok=True)
    with open(os.path.join(r, ".evidence", "audit", "z.jsonl"), "wb") as f:
        f.truncate(1 << 36)  # sparse: instant to make, 64 GiB to read
    t0 = time.time()
    got, reason = decision(run_hook(r, {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "ls"},
                                        "tool_use_id": "p58-big", "permission_mode": "default"})[0])
    check("REQ-IMH-20 an oversize audit log denies the call without reading it",
          got == "deny" and "larger than" in reason and time.time() - t0 < 15, (got, reason[:200], time.time() - t0))
    shutil.rmtree(r)

    # A2: a deleted snapshot plus broken git is still a violation, not "no repository"
    r = committed_repo()
    tid = "p58-a2-" + uuid.uuid4().hex[:6]
    p = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"}, "tool_use_id": tid,
         "permission_mode": "default"}
    run_hook(r, p, env_extra=KEY)
    cfgp = os.path.join(r, ".git", "config")
    good_cfg = open(cfgp).read()
    open(cfgp, "a").write("[\n")
    if os.path.lexists(integrity._snap_path("s1", tid)):
        os.remove(integrity._snap_path("s1", tid))
    obj, _ = run_hook(r, dict(p, hook_event_name="PostToolUse"), event="post", env_extra=KEY)
    note = obj.get("hookSpecificOutput", {}).get("additionalContext", "")
    check("REQ-IMH-23 a removed snapshot with git broken is recorded as integrity-snapshot-missing",
          "snapshot" in note and "missing" in note, note)
    open(cfgp, "w").write(good_cfg)
    shutil.rmtree(r)

    # A5: a control-plane directory that was already a symlink is reported, not silently skipped
    r = committed_repo()
    os.makedirs(os.path.join(r, "skills-src"))
    os.makedirs(os.path.join(r, ".claude"), exist_ok=True)
    os.symlink(os.path.join(r, "skills-src"), os.path.join(r, ".claude", "skills"))
    _, note = around(r, lambda: open(os.path.join(r, "skills-src", "x.md"), "w").write("x\n"), env=KEY)
    check("REQ-IMH-01 a pre-existing symlinked control-plane directory is reported", ".claude/skills" in note, note)
    shutil.rmtree(r)

    # B4 (owner decision 2026-09-25): a "don't ask again" grant written mid-call is kept and logged, not reverted
    r = committed_repo()
    os.makedirs(os.path.join(r, ".claude"), exist_ok=True)
    sl = os.path.join(r, ".claude", "settings.local.json")
    open(sl, "w").write(json.dumps({"permissions": {"allow": ["Bash(ls)"], "deny": ["Bash(rm:*)"]}}))
    grant = {"permissions": {"allow": ["Bash(ls)", "Bash(git status)"], "deny": ["Bash(rm:*)"]}}
    _, note = around(r, lambda: open(sl, "w").write(json.dumps(grant)), env=KEY)
    logged = any('"permission-grant"' in l for l in open(os.path.join(r, ".evidence", "audit", "s1.jsonl")))
    check("REQ-IMH-01 a permission grant added to settings.local.json during a call is kept and logged, not a violation",
          not note and json.load(open(sl)) == grant and logged and "permission-grant" not in vtext(r), (note, logged))
    widened = {"permissions": {"allow": ["Bash(ls)", "Bash(git status)"], "deny": []}}
    _, note = around(r, lambda: open(sl, "w").write(json.dumps(widened)), env=KEY)
    check("REQ-IMH-01 any other change to settings.local.json (a deny rule removed) is still restored and recorded",
          "settings.local.json" in note and json.load(open(sl)) == grant, note)
    bom = {"permissions": {"allow": ["Bash(ls)", "Bash(git status)", "Bash(make)"], "deny": ["Bash(rm:*)"]}}
    _, note = around(r, lambda: open(sl, "wb").write(b"\xef\xbb\xbf" + json.dumps(bom).encode()), env=KEY)
    check("REQ-IMH-01 an allow-only change re-encoded with a BOM is not taken as a permission grant",
          "settings.local.json" in note and json.load(open(sl)) == grant, note)
    shutil.rmtree(r)

    # nit 1: file_in_commit answers "present" (callers deny) when git cannot answer
    r = committed_repo()
    nogit = os.path.realpath(tempfile.mkdtemp(prefix="evidence-nogit-"))
    check("REQ-IMH-23 file_in_commit: present, absent, and git failure treated as present",
          st.file_in_commit(r, "HEAD", "src/app.py") and not st.file_in_commit(r, "HEAD", "src/nope.py")
          and st.file_in_commit(nogit, "HEAD", "src/app.py"))
    shutil.rmtree(nogit)
    shutil.rmtree(r)

    # Code review (step 11): dispatching a workflow from another ref is denied; from the default branch it isn't
    r = make_repo()
    for c in ("gh workflow run verify-range.yml --ref feature/ABC-1-x -f pr=5", "gh workflow run ci.yml -r feature/x",
              "gh workflow run verify-range.yml -rfeature/x -f pr=5", "gh workflow run ci.yml -r=feature/x",
              "gh api -X POST repos/o/r/actions/workflows/verify-range.yml/dispatches -f ref=feature/x"):
        t, i = bash(c)
        case(f"REQ-IMH-21 workflow dispatch from another ref denied: {c[:50]}", r, t, i, "deny", rule_hint="another ref")
    t, i = bash("gh workflow run ci.yml")
    case("REQ-IMH-21 control: a dispatch of the default branch's workflow is not denied by that rule", r, t, i, "allow")
    shutil.rmtree(r)

    # review item 10: an integrity check that raises is recorded as integrity-check-error, not swallowed
    import signing
    r = committed_repo()
    tid = "p58-err-" + uuid.uuid4().hex[:6]
    p = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"}, "tool_use_id": tid,
         "permission_mode": "default"}
    run_hook(r, p, env_extra=KEY)
    os.environ["EVIDENCE_SIGNING_KEY"] = KEY["EVIDENCE_SIGNING_KEY"]
    try:
        importlib.reload(signing)
        snap = json.load(open(integrity._snap_path("s1", tid)))
        snap = {k: v for k, v in snap.items() if k != "sig"}
        snap["cp"] = ["not", "a", "mapping"]  # signed, bound to the call, but malformed: check() raises
        st.write_file(tempfile.gettempdir(), integrity._snap_rel("s1", tid), json.dumps(signing.sign(snap)))
    finally:
        del os.environ["EVIDENCE_SIGNING_KEY"]
        importlib.reload(signing)
    obj, _ = run_hook(r, dict(p, hook_event_name="PostToolUse"), event="post", env_extra=KEY)
    note = obj.get("hookSpecificOutput", {}).get("additionalContext", "")
    check("REQ-SLF-09 an integrity check that raises is recorded as integrity-check-error",
          "integrity check for that command failed" in note and "integrity-check-error" in vtext(r), (note, vtext(r)[:300]))
    shutil.rmtree(r)

    # review item 11: the release-verify command runs without the signing key or GIT_* in its environment
    r = make_repo()
    envout = os.path.join(r, "verify-env.txt")
    org = os.path.join(r, "org.json")
    json.dump({"release_approval_pattern": "^REL-", "release_approval_verify_command": f"env > {envout}"}, open(org, "w"))
    t, i = bash("./deploy.sh production")
    case("REQ-IMH-22 release verify runs (valid approval allowed)", r, t, i, "allow",
         env=dict(KEY, RELEASE_APPROVAL="REL-1", EVIDENCE_ORG_POLICY=org))
    seen = open(envout).read() if os.path.isfile(envout) else ""
    check("REQ-IMH-22 the release-verify command's environment has no signing key and no GIT_*",
          seen and "EVIDENCE_SIGNING_KEY" not in seen and "\nGIT_" not in "\n" + seen, seen[:200] or "the command did not run")
    shutil.rmtree(r)

    # REQ-IMH-22: every engine subprocess call site is on the allow-list, exactly
    import ast
    eng = os.path.join(HERE, "..", "engine")
    sites = []
    for fn in sorted(glob.glob(os.path.join(eng, "*.py"))):
        tree = ast.parse(open(fn).read())
        mods = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
                if a.name in ("subprocess", "os")}
        if any(isinstance(n, ast.ImportFrom) and n.module in ("subprocess", "os") and any(
                a.name in ("run", "Popen", "call", "check_call", "check_output", "system", "popen") for a in n.names)
               for n in ast.walk(tree)):
            sites.append(f"{os.path.basename(fn)}:from-import")
        funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

        def owner(target):
            enclosing = [f for f in funcs if any(s is target for s in ast.walk(f))]
            return min(enclosing, key=lambda f: sum(1 for _ in ast.walk(f))).name if enclosing else "<module>"
        for sub in ast.walk(tree):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and isinstance(sub.func.value, ast.Name) \
                    and sub.func.value.id in mods and (sub.func.value.id != "os" or sub.func.attr in (
                        "system", "popen", "execv", "execvp", "execve", "spawnv", "spawnvp", "posix_spawn")):
                sites.append(f"{os.path.basename(fn)}:{owner(sub)}")
    allowed = {"state.py:run_git", "state.py:run_gh", "lifecycle.py:_ps_probe", "evidence_policy.py:_release_verify"}
    check("REQ-IMH-22 engine subprocesses start only from the allow-listed helpers (exact match)",
          set(sites) == allowed, sorted(set(sites) ^ allowed))


def suite_pilot62():
    """PILOT-62: the local layer is advisory behind the server gate (spec REQ-LLA-01..10)."""
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import types
    import uuid
    import state as st
    KEYV = "k" * 40
    KEY = {"EVIDENCE_SIGNING_KEY": KEYV}
    FIX = os.path.join(HERE, "fixtures", "pilot62")
    PUSH = "git push -u origin feature/ABC-1-login"

    class keyenv:
        """The fixture key (and any extra variables) in this process's environment, restored after."""

        def __init__(self, extra=None, key=True):
            # in-process engine calls see what a hook would: none of the variables BASE_ENV strips
            self.vars = {k: None for k in os.environ if k not in BASE_ENV}
            self.vars.update(extra or {})
            if key:
                self.vars["EVIDENCE_SIGNING_KEY"] = KEYV

        def __enter__(self):
            self.saved = {k: os.environ.get(k) for k in self.vars}
            for k, v in self.vars.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            return self

        def __exit__(self, *a):
            for k, v in self.saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def around(r, mutate, env=None, cmd="./vendor/tool", session="s1"):
        tid = "p62-" + uuid.uuid4().hex[:8]
        p = {"session_id": session, "cwd": r, "tool_name": "Bash", "tool_input": {"command": cmd}, "tool_use_id": tid,
             "permission_mode": "default"}
        pre = decision(run_hook(r, p, env_extra=env)[0])
        if pre[0] == "deny":
            return pre, ""
        mutate()
        obj, _ = run_hook(r, dict(p, hook_event_name="PostToolUse", tool_response={"stdout": ""}), event="post", env_extra=env)
        return pre, obj.get("hookSpecificOutput", {}).get("additionalContext", "")

    def entries(r):
        out = []
        for f in (glob.glob(os.path.join(r, ".evidence", "**", "violations*"), recursive=True)
                  + glob.glob(os.path.join(r, ".evidence", "violations", "*.json"))):
            if os.path.isfile(f):
                try:
                    d = json.load(open(f))
                except ValueError:
                    continue
                out += d.get("entries", []) if isinstance(d, dict) else d
        return out

    def events(r, session="s1"):
        p = os.path.join(r, ".evidence", "audit", f"{session}.jsonl")
        return [json.loads(l) for l in open(p)] if os.path.isfile(p) else []

    def sign_change(r, key="ABC-1"):
        cdir = os.path.join(r, ".evidence", "changes", key)
        with keyenv():
            st.save_state(r, key, json.load(open(os.path.join(cdir, "state.json"))))
            import signing
            ap = signing.sign(json.load(open(os.path.join(cdir, "approval.json"))))
            st.write_file(r, f".evidence/changes/{key}/approval.json", json.dumps(ap))

    def signed_repo(tier=1, claims=("src/app.py",), extra=None):
        r = make_repo()
        start_change(r, tier=tier, claims=claims)
        sign_change(r)
        if extra:
            extra(r)
        with keyenv():
            st.audit_append(r, "s0", {"event": "fixture"})  # a signed log to start from
        sh("git add -A && git commit -q -m 'ABC-1: c'", r)
        return r

    def push(r, env=KEY):
        obj, _ = run_hook(r, {"session_id": "s1", "cwd": r, "hook_event_name": "PreToolUse", "tool_name": "Bash",
                              "tool_input": {"command": PUSH}, "permission_mode": "default"}, env_extra=env)
        return decision(obj)

    def edit_src(r, env=KEY, perm="default", path="src/app.py"):
        t, i = edit(path)
        obj, _ = run_hook(r, {"session_id": "s1", "cwd": r, "hook_event_name": "PreToolUse", "tool_name": t,
                              "tool_input": i, "permission_mode": perm}, env_extra=env)
        return decision(obj)

    appr_rel = ".evidence/changes/ABC-1/approval.json"

    # ---------------- REQ-LLA-01: a verified undo is closed at birth and blocks nothing
    r = signed_repo()
    appr = os.path.join(r, appr_rel)
    original = open(appr).read()
    _, note = around(r, lambda: open(appr, "w").write('{"forged": true}'), env=KEY)
    e = [v for v in entries(r) if v.get("path") == appr_rel]
    check("REQ-LLA-01 a restored approval.json is recorded closed at birth (resolved=restored, resolved_at)",
          open(appr).read() == original and len(e) == 1 and e[0].get("open") is False and e[0].get("resolved") == "restored"
          and e[0].get("resolved_at") and e[0].get("action") == "restored", (e, note))
    ev = [x for x in events(r) if x.get("event") == "integrity-violation"]
    check("REQ-LLA-01 the restore is logged as an integrity-violation audit event marked resolved",
          any(x.get("resolved") == "restored" and x.get("violation_path") == appr_rel for x in ev), ev)
    check("REQ-LLA-01 the post-call note says the change was undone and there is nothing to clear",
          "restored" in note and "nothing to clear" in note and "clear-violations" not in note, note)
    got, reason = push(r)
    check("REQ-LLA-01 after a verified restore, push is not denied for integrity-violation",
          "integrity monitor" not in reason, reason)
    got, reason = edit_src(r)
    check("REQ-LLA-01 after a verified restore, a claimed source edit is allowed", got == "allow", reason)
    shutil.rmtree(r)

    r = signed_repo()
    pol = os.path.join(r, ".evidence", "policy.json")
    _, note = around(r, lambda: open(pol, "w").write("{}"), env=KEY)
    e = [v for v in entries(r) if v.get("path") == ".evidence/policy.json"]
    check("REQ-LLA-01 a created control-plane file that is removed is closed at birth",
          not os.path.exists(pol) and len(e) == 1 and e[0].get("action") == "removed" and e[0].get("open") is False
          and e[0].get("resolved") == "restored", (e, note))
    check("REQ-LLA-01 after a verified removal, push is not denied for integrity-violation and a source edit is allowed",
          "integrity monitor" not in push(r)[1] and edit_src(r)[0] == "allow", (push(r), edit_src(r)))
    shutil.rmtree(r)

    r = signed_repo()
    link = os.path.join(r, ".evidence", "secrets-allowlist.json")
    _, note = around(r, lambda: os.symlink("/etc/hosts", link), env=KEY)
    e = [v for v in entries(r) if v.get("path") == ".evidence/secrets-allowlist.json"]
    check("REQ-LLA-01 a planted control-plane symlink that is removed is closed at birth",
          not os.path.lexists(link) and len(e) == 1 and e[0].get("rule") == "control-plane-symlink"
          and e[0].get("open") is False and e[0].get("resolved") == "restored", (e, note))
    check("REQ-LLA-01 after a removed symlink, push is not denied for integrity-violation and a source edit is allowed",
          "integrity monitor" not in push(r)[1] and edit_src(r)[0] == "allow", (push(r), edit_src(r)))
    shutil.rmtree(r)

    # ---------------- REQ-LLA-02: everything not verifiably undone stays open and blocks
    r = make_repo()
    start_change(r)
    sh("git add -A && git commit -q -m 'ABC-1: c'", r)
    appr = os.path.join(r, appr_rel)
    _, note = around(r, lambda: open(appr, "w").write('{"forged": true}'))
    e = [v for v in entries(r) if v.get("path") == appr_rel]
    got, reason = push(r, env=None)
    check("REQ-LLA-02 unsigned mode: a control-plane change is recorded open, and push is denied",
          e and e[0].get("open") is True and "resolved" not in e[0] and got == "deny" and "integrity monitor" in reason,
          (e, reason))
    check("REQ-LLA-02 unsigned mode: a source edit stays denied", edit_src(r, env=None)[0] == "deny", edit_src(r, env=None))
    shutil.rmtree(r)

    def settings_file(r):
        os.makedirs(os.path.join(r, ".claude"), exist_ok=True)
        open(os.path.join(r, ".claude", "settings.json"), "w").write('{"a": 1}\n')
    r = signed_repo(extra=settings_file)
    cdir = os.path.join(r, ".claude")

    def forge_and_lock():
        open(os.path.join(cdir, "settings.json"), "w").write('{"a": 2}\n')
        os.chmod(cdir, 0o555)
    try:
        _, note = around(r, forge_and_lock, env=KEY)
    finally:
        os.chmod(cdir, 0o755)
    e = [v for v in entries(r) if v.get("path") == ".claude/settings.json"]
    got, reason = push(r)
    check("REQ-LLA-02 a restore whose write fails (read-only parent) stays open, and push and source edits are denied",
          e and e[0].get("open") is True and "resolved" not in e[0] and got == "deny" and "integrity monitor" in reason
          and edit_src(r)[0] == "deny", (e, note, reason))
    shutil.rmtree(r)

    # a re-read that differs from the snapshot (the file changed again after the restore): in-process test hook
    r = signed_repo()
    appr = os.path.join(r, appr_rel)
    note, e = "", []
    import evidence_policy as ep
    import hook
    import integrity
    with keyenv():
        tid = "p62-race-" + uuid.uuid4().hex[:6]
        payload = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"},
                   "tool_use_id": tid, "permission_mode": "default", "hook_event_name": "PostToolUse"}
        ctx = ep.Ctx(payload)
        integrity.snapshot(ctx)
        open(appr, "w").write('{"forged": true}')
        real_write = st.write_file

        def racing_write(root, rel, data):
            real_write(root, rel, data)
            if rel == appr_rel:
                with open(os.path.join(root, rel), "w") as f:
                    f.write('{"raced": true}')
        integrity.st.write_file = racing_write
        try:
            out = hook.run_integrity(ep.Ctx(payload))[0]
        finally:
            integrity.st.write_file = real_write
        note = ((out or {}).get("hookSpecificOutput") or {}).get("additionalContext", "")
    e = [v for v in entries(r) if v.get("path") == appr_rel]
    got, reason = push(r)
    check("REQ-LLA-02 a restore whose re-read differs from the snapshot stays open, says so, and push is denied",
          e and e[0].get("open") is True and "resolved" not in e[0] and "could not be verified" in note
          and got == "deny" and "integrity monitor" in reason, (e, note[:300], reason[:200]))
    shutil.rmtree(r)

    r = signed_repo()
    _, note = around(r, lambda: open(os.path.join(r, "src", "sneaky.py"), "w").write("x = 1\n"), env=KEY)
    e = [v for v in entries(r) if v.get("path") == "src/sneaky.py"]
    got, reason = push(r)
    check("REQ-LLA-02 an unclaimed source file written by an unparsed program stays open and push is denied",
          e and e[0].get("open") is True and "resolved" not in e[0] and got == "deny" and "integrity monitor" in reason,
          (e, reason))
    shutil.rmtree(r)

    r = signed_repo()
    with keyenv():
        for n in range(3):
            st.audit_append(r, "s1", {"event": "fixture", "n": n})
    log = os.path.join(r, ".evidence", "audit", "s1.jsonl")

    def truncate():
        lines = open(log).read().splitlines(True)
        open(log, "w").write("".join(lines[:1]))
    _, note = around(r, truncate, env=KEY)
    e = [v for v in entries(r) if v.get("rule") == "audit-tamper"]
    got, reason = push(r)
    check("REQ-LLA-02 an audit truncation stays open, and push and source edits are denied",
          e and e[0].get("open") is True and "resolved" not in e[0] and got == "deny" and edit_src(r)[0] == "deny",
          (e, note, reason))
    shutil.rmtree(r)

    # ---------------- REQ-LLA-03: the per-session cap
    r = signed_repo()
    appr = os.path.join(r, appr_rel)
    notes = []
    for n in range(4):
        notes.append(around(r, lambda: open(appr, "w").write('{"forged": %d}' % n), env=KEY)[1])
    e = [v for v in entries(r) if v.get("path") == appr_rel]
    got, reason = push(r)
    check("REQ-LLA-03 three restored changes in a session are closed; the fourth is open and push is denied",
          len(e) == 4 and [v.get("open") for v in e] == [False, False, False, True] and "resolved" not in e[3]
          and "auto_resolve_max_per_session" in notes[3] and got == "deny" and "integrity monitor" in reason,
          ([(v.get("open"), v.get("resolved")) for v in e], notes[3][:300], reason[:200]))
    _, note = around(r, lambda: open(appr, "w").write('{"forged": "other"}'), env=KEY, session="s9")
    e = [v for v in entries(r) if v.get("path") == appr_rel and v.get("session") == "s9"]
    check("REQ-LLA-03 the cap counts per session: another session's first restore is closed",
          e and e[0].get("open") is False, e)
    shutil.rmtree(r)

    zero = os.path.join(tempfile.gettempdir(), "evidence-test-org-p62-zero.json")
    json.dump({"unsigned_max_tier": 3, "auto_resolve_max_per_session": 0}, open(zero, "w"))
    r = signed_repo()
    appr = os.path.join(r, appr_rel)
    _, note = around(r, lambda: open(appr, "w").write('{"forged": true}'), env=dict(KEY, EVIDENCE_ORG_POLICY=zero))
    e = [v for v in entries(r) if v.get("path") == appr_rel]
    check("REQ-LLA-03 auto_resolve_max_per_session 0 disables auto-resolution: the first restore is open",
          e and e[0].get("open") is True and "integrity monitor" in push(r, env=dict(KEY, EVIDENCE_ORG_POLICY=zero))[1],
          (e, note))
    shutil.rmtree(r)
    os.remove(zero)

    merged_up = st._merge({"auto_resolve_max_per_session": 3}, {"auto_resolve_max_per_session": 10}, True)
    merged_down = st._merge({"auto_resolve_max_per_session": 3}, {"auto_resolve_max_per_session": 1}, True)
    merged_bad = st._merge({"auto_resolve_max_per_session": 3}, {"auto_resolve_max_per_session": "x"}, True)
    check("REQ-LLA-03 a repository policy may only lower auto_resolve_max_per_session (raise ignored, lower applied)",
          merged_up.get("auto_resolve_max_per_session") == 3 and merged_down.get("auto_resolve_max_per_session") == 1
          and merged_bad.get("auto_resolve_max_per_session") == 3, (merged_up, merged_down, merged_bad))
    r = signed_repo(extra=lambda r: open(os.path.join(r, ".evidence", "policy.json"), "w").write(
        json.dumps({"auto_resolve_max_per_session": 1})))
    appr = os.path.join(r, appr_rel)
    for n in range(2):
        around(r, lambda: open(appr, "w").write('{"forged": %d}' % n), env=KEY)
    e = [v for v in entries(r) if v.get("path") == appr_rel]
    check("REQ-LLA-03 a repository policy lowering the cap to 1 applies: the second restore is open",
          [v.get("open") for v in e] == [False, True], [(v.get("open"), v.get("resolved")) for v in e])
    shutil.rmtree(r)
    r = signed_repo(extra=lambda r: open(os.path.join(r, ".evidence", "policy.json"), "w").write(
        json.dumps({"auto_resolve_max_per_session": 50})))
    appr = os.path.join(r, appr_rel)
    for n in range(4):
        around(r, lambda: open(appr, "w").write('{"forged": %d}' % n), env=KEY)
    e = [v for v in entries(r) if v.get("path") == appr_rel]
    check("REQ-LLA-03 a repository policy raising the cap is ignored: the fourth restore is open",
          [v.get("open") for v in e] == [False, False, False, True], [(v.get("open"), v.get("resolved")) for v in e])
    shutil.rmtree(r)

    # ---------------- REQ-LLA-05: settings.local.json judged by effect
    base_sl = {"permissions": {"allow": ["Bash(ls)", "Bash(git status)"], "deny": ["Bash(rm:*)"],
                               "additionalDirectories": ["/tmp/a"]}, "model": "opus"}

    def sl_case(n, new, expect_kept, label, raw=None):
        r = signed_repo()
        os.makedirs(os.path.join(r, ".claude"), exist_ok=True)
        sl = os.path.join(r, ".claude", "settings.local.json")
        open(sl, "w").write(json.dumps(base_sl))
        sess = f"sl{n}"

        def mutate():
            if raw is not None:
                open(sl, "wb").write(raw)
            else:
                open(sl, "w").write(json.dumps(new))
        _, note = around(r, mutate, env=KEY, session=sess)
        now = open(sl, "rb").read()
        e = [v for v in entries(r) if v.get("path") == ".claude/settings.local.json"]
        evs = [x.get("event") for x in events(r, sess)]
        if expect_kept:
            ok = json.loads(now) == new and not e and not note and "config-change" in evs
        else:
            ok = json.loads(now) == base_sl and len(e) == 1 and e[0].get("open") is False and "settings.local.json" in note
        check(f"REQ-LLA-05 {label}", ok, (note[:200], e, evs, now[:200]))
        shutil.rmtree(r)

    p = base_sl["permissions"]
    sl_case(1, {"permissions": dict(p, allow=["Bash(ls)"]), "model": "opus"}, True,
            "an allow rule removed is kept and logged as config-change, not a violation")
    sl_case(2, {"permissions": dict(p, additionalDirectories=["/tmp/a", "/tmp/b"]), "model": "opus"}, True,
            "an additional directory added is kept")
    sl_case(3, {"permissions": dict(p, deny=["Bash(rm:*)", "Bash(curl:*)"], ask=["Bash(git push:*)"]), "model": "opus"}, True,
            "deny and ask rules added (tightening) are kept")
    sl_case(4, {"permissions": p, "model": "sonnet", "outputStyle": "Explanatory"}, True,
            "the kept display keys (model, outputStyle) changed are kept")
    sl_case(5, dict(base_sl, hooks={"PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": "true"}]}]}),
            False, "hooks added is restored (closed, resolved)")
    sl_case(6, dict(base_sl, disableAllHooks=True), False, "disableAllHooks: true is restored")
    sl_case(7, dict(base_sl, env={"EVIDENCE_ORG_POLICY": "/tmp/x"}), False, "env added is restored")
    sl_case(8, dict(base_sl, enabledPlugins={"x@y": True}), False, "enabledPlugins added is restored")
    sl_case(9, {"permissions": dict(p, deny=[]), "model": "opus"}, False, "a deny rule removed is restored")
    sl_case(10, {"permissions": dict(p, defaultMode="bypassPermissions"), "model": "opus"}, False,
            "permissions.defaultMode changed is restored")
    sl_case(11, dict(base_sl, statusLine={"type": "command", "command": "id"}), False, "statusLine added is restored")
    sl_case(12, None, False, "an allow-only change with a BOM is restored",
            raw=b"\xef\xbb\xbf" + json.dumps({"permissions": dict(p, allow=p["allow"] + ["Bash(make)"]), "model": "opus"}).encode())
    sl_case(13, None, False, "invalid JSON is restored", raw=b'{"permissions": ')

    # ---------------- REQ-LLA-06: system-managed config the user cannot write
    nuw = getattr(integrity, "_not_user_writable", None)
    scratch = os.path.realpath(tempfile.mkdtemp(prefix="evidence-p62-sys-"))
    sysf = os.path.join(scratch, "managed-settings.json")
    open(sysf, "w").write('{"a": 1}\n')
    check("REQ-LLA-06 _not_user_writable: true for a root-owned system file (/etc/hosts), false for a scratch file",
          nuw is not None and nuw("/etc/hosts") is True and nuw(sysf) is False,
          None if nuw is None else (nuw("/etc/hosts"), nuw(sysf)))
    org6 = os.path.join(scratch, "org.json")
    json.dump({"unsigned_max_tier": 3, "user_control_plane": [sysf], "user_config_not_charged": [sysf]}, open(org6, "w"))
    r = signed_repo()
    _, note = around(r, lambda: open(sysf, "w").write('{"a": 2}\n'), env=dict(KEY, EVIDENCE_ORG_POLICY=org6))
    e = [v for v in entries(r) if v.get("path") == sysf]
    check("REQ-LLA-06 a listed file the session's user could write is still hidden-change (negative)",
          e and e[0].get("rule") == "hidden-change" and e[0].get("open") is True, (e, note))
    shutil.rmtree(r)
    r = signed_repo()
    out, e, evs = "not run", [], []
    if nuw is not None:
        with keyenv({"EVIDENCE_ORG_POLICY": org6}):
            integrity._not_user_writable = lambda p: True
            try:
                tid = "p62-sys-" + uuid.uuid4().hex[:6]
                payload = {"session_id": "s1", "cwd": r, "tool_name": "Bash", "tool_input": {"command": "./vendor/tool"},
                           "tool_use_id": tid, "permission_mode": "default", "hook_event_name": "PostToolUse"}
                integrity.snapshot(ep.Ctx(payload))
                open(sysf, "w").write('{"a": 3}\n')
                out = hook.run_integrity(ep.Ctx(payload))[0]
            finally:
                integrity._not_user_writable = nuw
        e = [v for v in entries(r) if v.get("path") == sysf]
        evs = [x for x in events(r) if x.get("event") == "user-config-changed"]
    check("REQ-LLA-06 a system file the user cannot write (ownership stubbed) is logged as user-config-changed, not a violation",
          out is None and not e and evs and evs[0].get("config_path") == sysf and evs[0].get("old_hash")
          and evs[0].get("new_hash") and evs[0].get("old_hash") != evs[0].get("new_hash"), (out, e, evs))
    shutil.rmtree(r)
    shutil.rmtree(scratch)

    # ---------------- REQ-LLA-07: ~/.claude.json judged by its security projection
    home = os.path.realpath(tempfile.mkdtemp(prefix="evidence-p62-home-"))
    cj = os.path.join(home, ".claude.json")
    r = signed_repo()
    HENV = dict(KEY, HOME=home)
    doc = {"numStartups": 1, "tipsHistory": {"a": 1}, "projects": {r: {"allowedTools": ["Bash(ls)"], "lastCost": 1}}}
    json.dump(doc, open(cj, "w"))

    def rewrite(d):
        return lambda: json.dump(d, open(cj, "w"))
    _, note = around(r, rewrite(dict(doc, numStartups=2, projects={r: {"allowedTools": ["Bash(ls)"], "lastCost": 2},
                                                                      "/other": {"lastCost": 0}})), env=HENV)
    check("REQ-LLA-07 a bookkeeping rewrite of ~/.claude.json is not a violation",
          note == "" and not [v for v in entries(r) if v.get("path") == cj], (note, entries(r)))
    cur = json.load(open(cj))
    cur2 = json.loads(json.dumps(cur))
    cur2["projects"][r]["mcpServers"] = {"evil": {"command": "sh"}}
    _, note = around(r, rewrite(cur2), env=HENV)
    check("REQ-LLA-07 a projects.<repo>.mcpServers entry added to ~/.claude.json is hidden-change",
          any(v.get("path") == cj and v.get("rule") == "hidden-change" for v in entries(r)), (note, entries(r)))
    shutil.rmtree(r)
    r = signed_repo()
    json.dump(doc, open(cj, "w"))
    _, note = around(r, rewrite(dict(doc, mcpServers={"evil": {"command": "sh"}})), env=HENV)
    check("REQ-LLA-07 a top-level mcpServers added to ~/.claude.json is hidden-change",
          any(v.get("path") == cj and v.get("rule") == "hidden-change" for v in entries(r)), (note, entries(r)))
    shutil.rmtree(r)
    r = signed_repo()
    json.dump(doc, open(cj, "w"))
    _, note = around(r, lambda: open(cj, "w").write('{"numStartups": '), env=HENV)
    check("REQ-LLA-07 ~/.claude.json truncated to invalid JSON is hidden-change",
          any(v.get("path") == cj and v.get("rule") == "hidden-change" for v in entries(r)), (note, entries(r)))
    shutil.rmtree(r)
    r = signed_repo()
    json.dump(doc, open(cj, "w"))
    _, note = around(r, lambda: os.remove(cj), env=HENV)
    check("REQ-LLA-07 ~/.claude.json deleted is hidden-change",
          any(v.get("path") == cj and v.get("rule") == "hidden-change" for v in entries(r)), (note, entries(r)))
    shutil.rmtree(r)
    shutil.rmtree(home)

    # ---------------- REQ-LLA-09: gate detection reads GitHub through the pinned gh
    classic = json.load(open(os.path.join(FIX, "branch-classic.json")))
    rules = json.load(open(os.path.join(FIX, "rules-branch.json")))
    repo_json = json.load(open(os.path.join(FIX, "repo.json")))
    unprotected = {"name": "main", "protected": False, "protection": {"enabled": False,
                                                                      "required_status_checks": {"enforcement_level": "off",
                                                                                                 "contexts": [], "checks": []}}}

    def with_check(ctx_name="verify-range", app=15368, level="non_admins"):
        b = json.loads(json.dumps(classic))
        b["protection"]["required_status_checks"]["enforcement_level"] = level
        b["protection"]["required_status_checks"]["checks"] = [{"context": ctx_name, "app_id": app}]
        return b

    def fake_gh(d, branch, rules_body=None, fail=False, raw_branch=None):
        os.makedirs(d, exist_ok=True)
        json.dump(repo_json, open(os.path.join(d, "repo.json"), "w"))
        if raw_branch is not None:
            open(os.path.join(d, "branch.json"), "w").write(raw_branch)
        else:
            json.dump(branch, open(os.path.join(d, "branch.json"), "w"))
        json.dump(rules_body if rules_body is not None else [], open(os.path.join(d, "rules.json"), "w"))
        gh = os.path.join(d, "gh")
        open(gh, "w").write("#!/bin/sh\n"
                            f"echo \"$@\" >> {d}/gh.log\n"
                            + ("echo 'HTTP 502' >&2; exit 1\n" if fail else "")
                            + "case \"$*\" in\n"
                            f"  *rules/branches/*) cat {d}/rules.json;;\n"
                            f"  *branches/*) cat {d}/branch.json;;\n"
                            f"  *repos/o/r*) cat {d}/repo.json;;\n"
                            "  *) exit 1;;\n"
                            "esac\n")
        os.chmod(gh, 0o755)
        return gh

    def gh_calls(d):
        p = os.path.join(d, "gh.log")
        return open(p).read().splitlines() if os.path.isfile(p) else []

    def clear_calls(d):
        if os.path.isfile(os.path.join(d, "gh.log")):
            os.remove(os.path.join(d, "gh.log"))

    ci_gate = getattr(ep, "_ci_gate", None)
    pol0 = st.load_policy(os.path.realpath(tempfile.gettempdir()))

    def gate(root, gh, **polx):
        if ci_gate is None:
            return (None, "no _ci_gate", {})
        pol = json.loads(json.dumps({k: v for k, v in pol0.items() if not k.startswith("_")}))
        pol["approval"] = dict(pol.get("approval") or {}, github_repo=polx.pop("repo", "o/r"))
        pol.update(polx)
        ctx = types.SimpleNamespace(root=root, policy=pol, session="s1")
        with keyenv({"EVIDENCE_GH": gh}):
            return ci_gate(ctx)

    def scenario(label, expect, **kw):
        root = os.path.realpath(tempfile.mkdtemp(prefix="evidence-p62-gate-"))
        polx = kw.pop("polx", {})
        gh = fake_gh(os.path.join(root, "ghd"), **kw)
        res = gate(root, gh, **polx)
        check(f"REQ-LLA-09 {label}", res[0] is expect, (res, gh_calls(os.path.join(root, "ghd"))))
        return root, gh

    root, gh = scenario("classic protection with verify-range pinned to GitHub Actions confirms the gate", True,
                        branch=classic)
    # cache: served without a gh call; altered, expired and linked caches are ignored
    clear_calls(os.path.join(root, "ghd"))
    res = gate(root, gh)
    check("REQ-LLA-09 a confirmation is served from the signed cache without a gh call",
          res[0] is True and gh_calls(os.path.join(root, "ghd")) == [], (res, gh_calls(os.path.join(root, "ghd"))))
    cache_rel = getattr(ep, "_ci_gate_cache_rel", lambda r: "missing")(root)
    cache = os.path.join(tempfile.gettempdir(), cache_rel)
    cobj = json.load(open(cache)) if os.path.isfile(cache) else {}
    fake_gh(os.path.join(root, "ghd"), branch=unprotected)  # GitHub now says: not required
    altered = dict(cobj, at=cobj.get("at", 0) + 1)
    open(cache, "w").write(json.dumps(altered))
    res = gate(root, gh)
    check("REQ-LLA-09 an altered cache is ignored: gh is called again (and now says not confirmed)",
          res[0] is False and gh_calls(os.path.join(root, "ghd")) != [], (res, gh_calls(os.path.join(root, "ghd"))))
    fake_gh(os.path.join(root, "ghd"), branch=classic)
    clear_calls(os.path.join(root, "ghd"))
    with keyenv():
        import signing
        expired = signing.sign(dict({k: v for k, v in cobj.items() if k != "sig"}, at=cobj.get("at", 0) - 100000))
    open(cache, "w").write(json.dumps(expired))
    res = gate(root, gh)
    check("REQ-LLA-09 an expired cache is ignored: gh is called again",
          res[0] is True and gh_calls(os.path.join(root, "ghd")) != [] and cobj, (res, gh_calls(os.path.join(root, "ghd"))))
    clear_calls(os.path.join(root, "ghd"))
    good = open(cache).read()
    os.remove(cache)
    elsewhere = os.path.join(root, "planted.json")
    open(elsewhere, "w").write(good)
    os.symlink(elsewhere, cache)
    res = gate(root, gh)
    check("REQ-LLA-09 a cache replaced by a symlink is ignored: gh is called again",
          res[0] is True and gh_calls(os.path.join(root, "ghd")) != [], (res, gh_calls(os.path.join(root, "ghd"))))
    if os.path.lexists(cache):
        os.remove(cache)
    shutil.rmtree(root)
    for label, expect, kw in (
            ("rulesets with verify-range pinned (integration_id) confirm the gate", True,
             dict(branch=unprotected, rules_body=rules)),
            ("a check with app_id null (any source) does not confirm", False,
             dict(branch=with_check(app=None),
                  rules_body=[{"type": "required_status_checks",
                               "parameters": {"required_status_checks": [{"context": "verify-range"}]}}])),
            ("a check pinned to another app does not confirm", False, dict(branch=with_check(app=99))),
            ("the check missing does not confirm", False, dict(branch=with_check(ctx_name="build"))),
            ("gh exiting 1 does not confirm", False, dict(branch=classic, fail=True)),
            ("non-JSON output does not confirm", False, dict(branch=None, raw_branch="<html>not json</html>")),
            ("enforcement 'off' does not confirm", False, dict(branch=with_check(level="off"))),
            ("with ci_gate_require_enforce_admins, non_admins enforcement does not confirm", False,
             dict(branch=classic, polx={"ci_gate_require_enforce_admins": True})),
            ("with ci_gate_require_enforce_admins, 'everyone' enforcement confirms", True,
             dict(branch=with_check(level="everyone"), polx={"ci_gate_require_enforce_admins": True}))):
        root, _ = scenario(label, expect, **kw)
        shutil.rmtree(root)
    root = os.path.realpath(tempfile.mkdtemp(prefix="evidence-p62-gate-"))
    gh = fake_gh(os.path.join(root, "ghd"), branch=classic)
    res = gate(root, gh, repo="")
    check("REQ-LLA-09 an empty approval.github_repo does not confirm, and gh is never called",
          res[0] is False and gh_calls(os.path.join(root, "ghd")) == [] and "github_repo" in str(res[1]),
          (res, gh_calls(os.path.join(root, "ghd"))))
    shutil.rmtree(root)

    # ---------------- REQ-LLA-08: Tier 3 auto modes follow the confirmed gate
    ghdir = os.path.realpath(tempfile.mkdtemp(prefix="evidence-p62-gh-"))
    gh_ok = fake_gh(os.path.join(ghdir, "ok"), branch=classic)
    gh_bad = fake_gh(os.path.join(ghdir, "bad"), branch=unprotected)
    org8 = os.path.join(ghdir, "org.json")
    json.dump({"unsigned_max_tier": 3, "approval": {"github_repo": "o/r"}}, open(org8, "w"))
    org8off = os.path.join(ghdir, "org-off.json")
    json.dump({"unsigned_max_tier": 3, "approval": {"github_repo": "o/r"}, "tier3_auto_modes_with_required_gate": False},
              open(org8off, "w"))
    E8 = dict(KEY, EVIDENCE_ORG_POLICY=org8, EVIDENCE_GH=gh_ok)
    r = signed_repo(tier=3, claims=("src/**",))
    for mode in ("auto", "acceptEdits"):
        got, reason = edit_src(r, env=E8, perm=mode, path="src/auth/login.py")
        check(f"REQ-LLA-08 a Tier 3 edit in {mode} mode is allowed when the gate is confirmed", got == "allow", reason)
    check("REQ-LLA-08 a tier3-auto-mode-allowed audit event records the gate evidence",
          any(x.get("event") == "tier3-auto-mode-allowed" and x.get("gate") for x in events(r)), [x.get("event") for x in events(r)])
    for mode in ("bypassPermissions", "dontAsk"):
        got, reason = edit_src(r, env=E8, perm=mode, path="src/auth/login.py")
        check(f"REQ-LLA-08 a Tier 3 edit in {mode} mode stays denied with the gate confirmed", got == "deny", reason)
    got, reason = edit_src(r, env=dict(E8, EVIDENCE_SIGNING_KEY=None), perm="auto", path="src/auth/login.py")
    check("REQ-LLA-08 an unsigned session's Tier 3 auto-mode edit is denied, naming the missing key",
          got == "deny" and "sign" in reason.lower(), reason)
    got, reason = edit_src(r, env=dict(E8, EVIDENCE_ORG_POLICY=org8off), perm="auto", path="src/auth/login.py")
    check("REQ-LLA-08 the flag false in the org policy denies the Tier 3 auto-mode edit",
          got == "deny" and "tier3_auto_modes_with_required_gate" in reason, reason)
    shutil.rmtree(r)
    r = signed_repo(tier=3, claims=("src/**",), extra=lambda r: open(os.path.join(r, ".evidence", "policy.json"), "w").write(
        json.dumps({"tier3_auto_modes_with_required_gate": True})))
    got, reason = edit_src(r, env=dict(E8, EVIDENCE_ORG_POLICY=org8off), perm="auto", path="src/auth/login.py")
    check("REQ-LLA-08 a repository policy setting the flag true when the org sets it false is ignored (denied)",
          got == "deny" and "tier3_auto_modes_with_required_gate" in reason, reason)
    shutil.rmtree(r)
    r = signed_repo(tier=3, claims=("src/**",))
    got, reason = edit_src(r, env=dict(E8, EVIDENCE_GH=gh_bad), perm="auto", path="src/auth/login.py")
    check("REQ-LLA-08 when the gate is not confirmed the denial names the cause and the owner action",
          got == "deny" and "verify-range" in reason and "not required" in reason, reason)
    shutil.rmtree(r)
    r = signed_repo(tier=3, claims=("src/**",))
    got, reason = edit_src(r, env=dict(KEY, EVIDENCE_GH=gh_ok), perm="auto", path="src/auth/login.py")
    check("REQ-LLA-08 with no approval.github_repo the Tier 3 auto-mode edit is denied, naming it",
          got == "deny" and "github_repo" in reason, reason)
    shutil.rmtree(r)
    shutil.rmtree(ghdir)

    # ---------------- REQ-LLA-10: creating a commit status or check run is check-forgery
    r = make_repo()
    for c in ("gh api -X POST repos/o/r/statuses/abc -f state=success -f context=verify-range",
              "gh api repos/o/r/statuses/abc -f state=success",
              "gh api repos/o/r/check-runs -X POST -f name=verify-range -f head_sha=abc",
              "gh api --method=PATCH repos/o/r/check-runs/1 -f conclusion=success",
              "gh api -XPOST repos/o/r/check-suites -f head_sha=abc",
              "gh api repos/o/r/check-runs --input run.json"):
        t, i = bash(c)
        case(f"REQ-LLA-10 check-forgery denied: {c[:60]}", r, t, i, "deny", rule_hint="commit status or check run")
    for c in ("gh api repos/o/r/commits/abc/check-runs", "gh api repos/o/r/commits/abc/statuses",
              "gh api repos/o/r/commits/abc/status"):
        t, i = bash(c)
        case(f"REQ-LLA-10 reading checks or statuses is allowed: {c[:60]}", r, t, i, "allow")
    shutil.rmtree(r)


if __name__ == "__main__":
    for fn in [suite_pilot62, suite_pilot58,suite_audit_concurrency_and_hook_scope, suite_signed_lifecycle, suite_round5, suite_round4, suite_reaudit_fixes, suite_integrity, suite_gate_true_positives, suite_mutation, suite_self_review, suite_historic, suite_fail_closed, suite_no_change, suite_control_plane, suite_change_rules, suite_fix_mode,
               suite_push_merge, suite_commit, suite_deploy, suite_policy_merge, suite_audit_and_session]:
        fn()
    print(f"\n{results['pass']} passed, {results['fail']} failed")
    if os.environ.get("JUNIT_OUT"):
        write_junit(os.environ["JUNIT_OUT"], "evidence-sdlc gate engine")
    sys.exit(1 if results["fail"] else 0)
