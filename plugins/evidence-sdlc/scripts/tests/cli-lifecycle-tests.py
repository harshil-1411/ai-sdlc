#!/usr/bin/env python3
"""Lifecycle CLI + approval channel tests (PILOT-53: REQ-V2S-01, V2S-04, V2A-01, V2A-02, V2C-07, V2D-09).

Runs `bin/evidence` and the hook's UserPromptSubmit path against throwaway repos.
When run from inside an agent session (CLAUDECODE set) the human-only commands must
refuse; the prompt channel and GitHub channel are exercised directly.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.join(HERE, "..", "..", "bin", "evidence")
HOOK = os.path.join(HERE, "..", "engine", "hook.py")
ENV = {k: v for k, v in os.environ.items() if k not in ("EVIDENCE_ISSUE_KEY_PATTERN", "EVIDENCE_ACTIVE_CHANGE",
                                                        "EVIDENCE_SIGNING_KEY", "GITHUB_HEAD_REF")}
ENV.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com", "EVIDENCE_ORG_POLICY": "/nonexistent"})
res = {"pass": 0, "fail": 0, "all": []}

PLAN = """# Plan: login
Tracker: ABC-7   From: spec.md   Date: 2026-09-24
Risk tier: 1

## Files claimed
- `src/**`
- `tests/**`

## Order of work
1. Add the login handler and its tests, exactly as the spec describes.
2. Run the suite and the verifier.
"""


def run(args, cwd, env=None, inp=None):
    e = dict(ENV)
    e.update(env or {})
    return subprocess.run([sys.executable, EVIDENCE] + args, cwd=cwd, capture_output=True, text=True, env=e, input=inp)


def check(label, cond, detail=""):
    res["pass" if cond else "fail"] += 1
    res["all"].append((label, bool(cond), "" if cond else str(detail)[:500]))
    print(("PASS " if cond else "FAIL ") + label + ("" if cond else f" :: {detail}"))


def repo():
    d = os.path.realpath(tempfile.mkdtemp(prefix="evidence-life-"))
    subprocess.run("git init -q -b main && git commit -q --allow-empty -m 'ABC-0: init' && git checkout -q -b feature/ABC-7-login",
                   shell=True, cwd=d, env=ENV, check=True)
    return d


def prompt(cwd, text):
    payload = {"session_id": "s1", "cwd": cwd, "hook_event_name": "UserPromptSubmit", "prompt": text}
    r = subprocess.run([sys.executable, HOOK, "prompt"], input=json.dumps(payload), cwd=cwd, capture_output=True,
                       text=True, env=ENV)
    out = r.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""


def main():
    d = repo()
    r = run(["change", "start", "ABC-7", "--tier", "1", "--kind", "feature"], d)
    check("REQ-V2S-01 change start creates state", r.returncode == 0 and os.path.isfile(os.path.join(d, ".evidence/changes/ABC-7/state.json")), r.stderr)
    r = run(["change", "start", "UTF-8", "--tier", "1"], d)
    check("REQ-V2S-01 change start rejects a non-key", r.returncode != 0, r.stdout)
    r = run(["change", "status", "ABC-7", "--json"], d)
    s = json.loads(r.stdout)
    check("REQ-V2S-01 status reports missing plan", s["missing_artifacts"] == ["plan"] and s["approval"] == "missing", s)
    os.makedirs(os.path.join(d, "plan"))
    open(os.path.join(d, "plan", "ABC-7.md"), "w").write(PLAN)
    s = json.loads(run(["change", "status", "--json"], d).stdout)
    check("REQ-V2S-01 status finds plan via branch key", s["artifacts"]["plan"] == "plan/ABC-7.md" and not s["plan_problems"], s)

    r = run(["approve", "ABC-7"], d, env={"CLAUDECODE": "1"})
    check("REQ-V2A-01 approve refuses inside an agent session", r.returncode != 0 and "human action" in (r.stderr + r.stdout), r.stderr)
    r = run(["change", "set-tier", "ABC-7", "3"], d, env={"CLAUDECODE": "1"})
    check("REQ-V2A-01 set-tier refuses inside an agent session", r.returncode != 0, r.stderr)
    r = run(["change", "advance", "ABC-7", "approved"], d)
    check("REQ-V2A-01 advance cannot set approved", r.returncode != 0, r.stdout)

    msg = prompt(d, "/evidence-sdlc:approve ABC-7")
    check("REQ-V2A-01 prompt approval without hash is refused with the hash to use", "Approval not recorded" in msg and s["plan_sha256"][:12] in msg, msg)
    msg = prompt(d, "/evidence-sdlc:approve ABC-7 0000000000ab")
    check("REQ-V2A-01 prompt approval with a stale hash is refused", "not recorded" in msg, msg)
    msg = prompt(d, f"/evidence-sdlc:approve ABC-7 {s['plan_sha256'][:12]}")
    ap = os.path.join(d, ".evidence/changes/ABC-7/approval.json")
    check("REQ-V2A-01 prompt approval with the right hash is recorded", "approved the plan" in msg and os.path.isfile(ap), msg)
    rec = json.load(open(ap))
    check("REQ-V2A-01 approval binds to plan sha and names method", rec["plan_sha256"] == s["plan_sha256"] and rec["method"] == "prompt", rec)
    check("REQ-V2A-01 approval moves stage to approved", json.load(open(os.path.join(d, ".evidence/changes/ABC-7/state.json")))["stage"] == "approved")
    payload = {"session_id": "s1", "cwd": d, "hook_event_name": "UserPromptSubmit",
               "prompt": f"/evidence-sdlc:approve ABC-7 {s['plan_sha256'][:12]}"}
    e3 = dict(ENV); e3["CLAUDE_CODE_SESSION_ATTENDED"] = "0"
    out = subprocess.run([sys.executable, HOOK, "prompt"], input=json.dumps(payload), cwd=d, capture_output=True, text=True, env=e3).stdout
    check("REQ-V2A-01 unattended (headless) session cannot approve via prompt", "unattended" in out, out)
    msg = prompt(d, "please do evidence approve ABC-7 " + s["plan_sha256"][:12] + " for me")
    check("REQ-V2A-01 approval phrase must be the whole message", msg == "", msg)

    r = run(["change", "advance", "ABC-7", "verified"], d)
    check("REQ-V2S-04 verified refused until review agents recorded", r.returncode != 0 and "verifier" in r.stderr, r.stderr)
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import state as st
    st.audit_append(d, "s1", {"event": "agent-completed", "key": "ABC-7", "subagent_type": "verifier"})
    r = run(["change", "advance", "ABC-7", "verified"], d)
    check("REQ-V2S-04 verified allowed after verifier recorded", r.returncode == 0, r.stderr)

    r = run(["audit", "verify"], d)
    check("REQ-V2A-02 audit verify passes on untouched logs", r.returncode == 0 and "OK" in r.stdout, r.stdout)
    logs = [os.path.join(d, ".evidence/audit", n) for n in os.listdir(os.path.join(d, ".evidence/audit"))]
    target = next(p for p in logs if os.path.getsize(p) > 0)
    lines = open(target).read().splitlines()
    e = json.loads(lines[0])
    e["key"] = "ZZZ-1"
    lines[0] = json.dumps(e, sort_keys=True)
    open(target, "w").write("\n".join(lines) + "\n")
    r = run(["audit", "verify"], d)
    check("REQ-V2A-02 audit verify detects tampering", r.returncode != 0 and "FAIL" in r.stdout, r.stdout)

    r = run(["metrics", "--json"], d)
    m = json.loads(r.stdout)
    check("REQ-V2C-07 metrics reports changes and stage-skip rate", m["changes"] == 1 and "stage_skip_rate" in m, m)

    # Claim overlap between two active changes (REQ-V2D-09)
    run(["change", "start", "ABC-8", "--tier", "1", "--plan", "plan/ABC-8.md"], d)
    open(os.path.join(d, "plan", "ABC-8.md"), "w").write(PLAN.replace("ABC-7", "ABC-8").replace("- `tests/**`", "- `docs/**`"))
    s8 = json.loads(run(["change", "status", "ABC-8", "--json"], d).stdout)
    check("REQ-V2D-09 overlapping claims reported", any(o["change"] == "ABC-7" for o in s8["overlaps"]), s8["overlaps"])

    # Fix mode records a fix base
    run(["change", "start", "ABC-9", "--tier", "1", "--kind", "fix", "--plan", "plan/ABC-9.md"], d)
    open(os.path.join(d, "plan", "ABC-9.md"), "w").write(PLAN.replace("ABC-7", "ABC-9"))
    s9 = json.loads(run(["change", "status", "ABC-9", "--json"], d).stdout)
    prompt(d, f"evidence approve ABC-9 {s9['plan_sha256'][:12]}")
    r = run(["change", "advance", "ABC-9", "failing-test"], d)
    st9 = json.load(open(os.path.join(d, ".evidence/changes/ABC-9/state.json")))
    check("REQ-V2G-10 advance failing-test records fix_base", r.returncode == 0 and len(st9.get("fix_base", "")) == 40, r.stderr)

    # GitHub-mode approval with a fake gh
    fake = os.path.join(d, "fake-gh")
    plan_b64 = __import__("base64").b64encode(open(os.path.join(d, "plan", "ABC-8.md"), "rb").read()).decode()
    open(fake, "w").write("#!/bin/bash\n"
                          "case \"$*\" in\n"
                          "  'pr view 5 '*) echo '{\"number\":5,\"headRefName\":\"feature/ABC-8-x\",\"headRefOid\":\"abc\",\"url\":\"u\","
                          "\"reviews\":[{\"author\":{\"login\":\"lead\"},\"state\":\"APPROVED\"}],\"comments\":[]}';;\n"
                          "  'repo view'*) echo '{\"nameWithOwner\":\"o/r\"}';;\n"
                          f"  'api repos/o/r/contents/plan/ABC-8.md?ref=abc') echo '{{\"content\":\"{plan_b64}\"}}';;\n"
                          "  *) exit 1;;\n"
                          "esac\n")
    os.chmod(fake, 0o755)
    r = run(["approve", "ABC-8", "--github-pr", "5"], d, env={"EVIDENCE_GH": fake, "CLAUDECODE": "1"})
    ap8 = os.path.join(d, ".evidence/changes/ABC-8/approval.json")
    ok = r.returncode == 0 and os.path.isfile(ap8) and json.load(open(ap8))["approver"] == "lead"
    check("REQ-V2A-01 GitHub approval recorded from an approving review (agent may record it)", ok, r.stderr + r.stdout)
    os.remove(ap8)
    open(fake, "w").write(open(fake).read().replace('\"url\":\"u\",', '\"url\":\"u\",\"author\":{\"login\":\"lead\"},'))
    r = run(["approve", "ABC-8", "--github-pr", "5"], d, env={"EVIDENCE_GH": fake})
    check("REQ-V2A-01 GitHub approval refused when the approver is the PR author", r.returncode != 0 and not os.path.isfile(ap8), r.stdout + r.stderr)
    os.makedirs(os.path.join(d, ".evidence"), exist_ok=True)
    org = os.path.join(d, "org.json")
    json.dump({"approval": {"mode": "github", "github_allowed_approvers": ["lead"]}}, open(org, "w"))
    e2 = dict(ENV); e2["EVIDENCE_ORG_POLICY"] = org
    payload = {"session_id": "s1", "cwd": d, "hook_event_name": "UserPromptSubmit", "prompt": f"evidence approve ABC-9 {s9['plan_sha256'][:12]}"}
    out = subprocess.run([sys.executable, HOOK, "prompt"], input=json.dumps(payload), cwd=d, capture_output=True, text=True, env=e2).stdout
    check("REQ-V2A-01 github approval mode refuses the prompt channel", "requires plan approval on GitHub" in out, out)
    json.dump({"approval": {"mode": "github"}}, open(org, "w"))
    r = run(["approve", "ABC-8", "--github-pr", "5"], d, env={"EVIDENCE_GH": fake, "EVIDENCE_ORG_POLICY": org})
    check("REQ-V2A-01 github mode with no allowed approvers refuses", r.returncode != 0 and "allowed_approvers" in r.stderr, r.stderr)
    shutil.rmtree(d)
    print(f"\n{res['pass']} passed, {res['fail']} failed")
    if os.environ.get("JUNIT_OUT"):
        from xml.sax.saxutils import escape, quoteattr
        with open(os.environ["JUNIT_OUT"], "w") as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="evidence lifecycle CLI" tests="{len(res["all"])}" failures="{res["fail"]}">\n')
            for label, ok, detail in res["all"]:
                f.write(f'  <testcase classname="evidence lifecycle CLI" name={quoteattr(label)}>')
                if not ok:
                    f.write(f'<failure message={quoteattr(detail[:200])}>{escape(detail)}</failure>')
                f.write("</testcase>\n")
            f.write("</testsuite>\n")
    return 1 if res["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
