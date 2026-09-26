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


def signed_terminal_tests():
    """PILOT-57: human terminal actions (spec D1, D7)."""
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import lifecycle
    # REQ-SLF-01: a real terminal is not seekable; the confirmation channel must still work on one
    saved = {k: os.environ.pop(k) for k in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT") if k in os.environ}
    label = "REQ-SLF-01 the human-terminal check reads and writes a real (non-seekable) terminal"
    try:
        master, slave = os.openpty()
    except OSError as e:
        # A sandbox without pseudo-terminals records no result, so this is not proof there; CI (Linux) runs it.
        print(f"SKIP {label}: no pseudo-terminal here ({e})")
        master = None
    if master is not None:
        try:
            tty = lifecycle._human_tty(os.ttyname(slave))
            tty.write("Type the key to confirm: ")
            tty.flush()
            os.write(master, b"ABC-7\n")
            line = tty.readline().strip()
            prompt_seen = os.read(master, 200)
            check(label, line == "ABC-7" and b"confirm" in prompt_seen, (line, prompt_seen))
        except Exception as e:
            check(label, False, repr(e))
        finally:
            os.close(master)
            os.close(slave)
    os.environ.update(saved)
    try:
        os.environ["CLAUDECODE"] = "1"
        lifecycle._human_tty()
        refused = False
    except lifecycle.HumanOnly:
        refused = True
    finally:
        os.environ.pop("CLAUDECODE", None)
        os.environ.update(saved)
    check("REQ-SLF-01 the human-terminal check still refuses inside Claude Code", refused)

    # REQ-SLF-05: in a signed deployment, a terminal without the key must not write unsigned records
    d = repo()
    os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
    import importlib, signing, state as st
    importlib.reload(signing)
    st.save_state(d, "ABC-7", {"key": "ABC-7", "tier": 1, "kind": "feature", "stage": "plan"})
    del os.environ["EVIDENCE_SIGNING_KEY"]
    importlib.reload(signing)
    before = open(os.path.join(d, ".evidence", "changes", "ABC-7", "state.json")).read()
    human = {k: v for k, v in ENV.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    for args in (["change", "clear-violations", "ABC-7"], ["change", "set-tier", "ABC-7", "2"], ["change", "release", "ABC-7"],
                 ["approve", "ABC-7"]):
        r = subprocess.run([sys.executable, EVIDENCE] + args, cwd=d, capture_output=True, text=True, env=human,
                           stdin=subprocess.DEVNULL)
        check(f"REQ-SLF-05 `evidence {' '.join(args[:2])}` without the key in a signed repo refuses and names the key",
              r.returncode != 0 and "EVIDENCE_SIGNING_KEY" in (r.stderr + r.stdout)
              and open(os.path.join(d, ".evidence", "changes", "ABC-7", "state.json")).read() == before
              and not os.path.exists(os.path.join(d, ".evidence", "changes", "ABC-7", "approval.json")), r.stderr + r.stdout)
    shutil.rmtree(d)
    # a repository whose only signed record is a violations file is still recognised as signed
    for rel in (os.path.join("changes", "ABC-7", "violations.json"), os.path.join("violations", "feature_ABC-7-login.json")):
        d = repo()
        os.environ["EVIDENCE_SIGNING_KEY"] = "k" * 40
        importlib.reload(signing)
        p = os.path.join(d, ".evidence", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(signing.sign({"entries": []}), open(p, "w"))
        del os.environ["EVIDENCE_SIGNING_KEY"]
        importlib.reload(signing)
        r = subprocess.run([sys.executable, EVIDENCE, "change", "clear-violations", "ABC-7"], cwd=d, capture_output=True,
                           text=True, env=human, stdin=subprocess.DEVNULL)
        check(f"REQ-SLF-05 a signed .evidence/{rel.split(os.sep)[0]}/… violations file alone marks the repository as signed",
              r.returncode != 0 and "EVIDENCE_SIGNING_KEY" in (r.stderr + r.stdout), r.stderr + r.stdout)
        shutil.rmtree(d)


VR_KEY = "v" * 40
VR_PLAN = PLAN.replace("- `tests/**`", "- `tests/**`\n- `plan/ABC-7.md`")


def vr_git(d, cmd, env=None):
    e = dict(ENV)
    e.update(env or {})
    return subprocess.run(cmd, shell=True, cwd=d, env=e, check=True, capture_output=True, text=True).stdout.strip()


class Signed:
    """Build signed records in-process with the fixture key, then restore the environment."""

    def __enter__(self):
        sys.path.insert(0, os.path.join(HERE, "..", "engine"))
        import importlib, signing, state
        self.saved = os.environ.get("EVIDENCE_SIGNING_KEY")
        os.environ["EVIDENCE_SIGNING_KEY"] = VR_KEY
        importlib.reload(signing)
        self.st, self.signing = state, signing
        return self

    def __exit__(self, *a):
        import importlib
        if self.saved is None:
            os.environ.pop("EVIDENCE_SIGNING_KEY", None)
        else:
            os.environ["EVIDENCE_SIGNING_KEY"] = self.saved
        importlib.reload(self.signing)


def vr_commit(d, msg, session="s1", trailer=None, audit=True):
    """Commit everything with `msg`; unless told otherwise, append to the session log first and add the trailer."""
    if audit and session:
        with Signed() as s:
            s.st.audit_append(d, session, {"event": "tool", "key": "ABC-7", "msg": msg})
    body = msg + "\n\n" + (trailer if trailer is not None else f"Agent-Session: {session}")
    open(os.path.join(d, ".git", "MSG"), "w").write(body + "\n")
    vr_git(d, "git add -A && git commit -q --allow-empty -F .git/MSG")
    return vr_git(d, "git rev-parse HEAD")


def vr_state(d, key="ABC-7", stage="implementing", **extra):
    with Signed() as s:
        s.st.save_state(d, key, dict({"key": key, "tier": 1, "kind": "feature", "stage": stage}, **extra))


def vr_approval(d, key="ABC-7", plan="plan/ABC-7.md"):
    with Signed() as s:
        rec = s.signing.sign({"key": key, "plan_path": plan, "plan_sha256": s.st.sha256_file(os.path.join(d, plan)),
                              "approver": "lead", "method": "github", "approved_at": "2026-09-25T00:00:00Z"})
        s.st.write_file(d, f".evidence/changes/{key}/approval.json", json.dumps(rec, indent=2, sort_keys=True) + "\n")


def vr_fixture(codeowners="* @lead\n", base_extra=None):
    """main: CODEOWNERS, src/app.py, README.md; feature/ABC-7-login: an approved plan, signed state, an audit log,
    and one claimed code change -- the shape of a clean PR. Returns (dir, base sha, head sha)."""
    d = os.path.realpath(tempfile.mkdtemp(prefix="evidence-vr-"))
    vr_git(d, "git init -q -b main")
    os.makedirs(os.path.join(d, ".github"))
    os.makedirs(os.path.join(d, "src"))
    open(os.path.join(d, ".github", "CODEOWNERS"), "w").write(codeowners)
    open(os.path.join(d, "src", "app.py"), "w").write("v = 0\n")
    open(os.path.join(d, "README.md"), "w").write("readme\n")
    if base_extra:
        base_extra(d)
    vr_git(d, "git add -A && git commit -q -m 'ABC-0: base'")
    base = vr_git(d, "git rev-parse HEAD")
    vr_git(d, "git checkout -q -b feature/ABC-7-login")
    os.makedirs(os.path.join(d, "plan"), exist_ok=True)
    open(os.path.join(d, "plan", "ABC-7.md"), "w").write(VR_PLAN)
    vr_state(d)
    vr_approval(d)
    vr_commit(d, "ABC-7: plan")
    open(os.path.join(d, "src", "app.py"), "w").write("v = 1\n")
    head = vr_commit(d, "ABC-7: implement")
    return d, base, head


def vr_run(d, base, head, reviews=None, env=None, event=None, author="dev", ref="feature/ABC-7-login", pull_ref=True,
           org=None, event_name="pull_request_target", args=()):
    """Run `evidence verify-range` as the base-branch workflow would: event file, token, key, a stub gh."""
    reviews = reviews if reviews is not None else [{"user": {"login": "lead"}, "state": "APPROVED", "commit_id": head}]
    pr = {"number": 5, "base": {"sha": base, "ref": "main"}, "head": {"sha": head, "ref": ref}, "user": {"login": author}}
    ev = event if event is not None else {"pull_request": pr}
    tmp = tempfile.mkdtemp(prefix="evidence-vr-ev-")
    for name, obj in (("event.json", ev), ("reviews.json", reviews), ("pull.json", pr)):
        json.dump(obj, open(os.path.join(tmp, name), "w"))
    gh = os.path.join(tmp, "gh")
    open(gh, "w").write("#!/bin/sh\n"
                        f"echo \"$@\" >> {tmp}/gh.log\n"
                        "case \"$*\" in\n"
                        f"  *pulls/5/reviews*) cat {tmp}/reviews.json;;\n"
                        f"  *pulls/5*) cat {tmp}/pull.json;;\n"
                        "  *) exit 1;;\n"
                        "esac\n")
    os.chmod(gh, 0o755)
    if pull_ref and head:
        vr_git(d, f"git update-ref refs/pull/5/head {pull_ref if isinstance(pull_ref, str) else head}")
    e = {"EVIDENCE_SIGNING_KEY": VR_KEY, "GH_TOKEN": "t", "GITHUB_REPOSITORY": "o/r", "GITHUB_EVENT_PATH": os.path.join(tmp, "event.json"),
         "GITHUB_EVENT_NAME": event_name, "EVIDENCE_GH": gh, "GITHUB_ACTIONS": "true"}
    if org:
        json.dump(org, open(os.path.join(tmp, "org.json"), "w"))
        e["EVIDENCE_ORG_POLICY"] = os.path.join(tmp, "org.json")
    e.update(env or {})
    e = {k: v for k, v in e.items() if v is not None}
    r = run(["verify-range"] + list(args), d, env=e)
    shutil.rmtree(tmp)
    return r


def vr_expect(label, r, rule):
    out = (r.stdout + r.stderr).lower()
    if rule is None:
        check(f"REQ-IMH-19 passes: {label}", r.returncode == 0, r.stdout[-600:] + r.stderr[-600:])
    else:
        check(f"REQ-IMH-19 rule {rule} fails: {label}", r.returncode != 0 and f"rule {rule}" in out and "traceback" not in out,
              (r.returncode, r.stdout[-600:] + r.stderr[-600:]))


def _vr_shared_log(d):
    with Signed() as s:
        s.st.audit_append(d, "clear-violations", {"event": "violations-cleared", "key": "ABC-0"})


def verify_range_tests():
    """PILOT-58 REQ-IMH-19: `evidence verify-range` per ADR-0004 rules 0-7, on fixture repositories."""
    def case(label, rule, mutate=None, fixture=None, **kw):
        d, base, head = (fixture or vr_fixture)()
        if mutate:
            got = mutate(d, base, head)
            if isinstance(got, dict):
                kw = dict(got, **kw)
                base, head = kw.pop("base", base), kw.pop("head", head)
            elif got:
                head = got
        vr_expect(label, vr_run(d, base, head, **kw), rule)
        shutil.rmtree(d)

    def w(d, rel, text):
        os.makedirs(os.path.dirname(os.path.join(d, rel)) or d, exist_ok=True)
        open(os.path.join(d, rel), "w").write(text)

    case("a clean branch", None)
    # rule 0: fail closed on bad input
    case("empty base SHA", 0, lambda d, b, h: {"base": ""})
    case("non-hex head SHA", 0, lambda d, b, h: {"head": "zz" * 20, "pull_ref": False})
    case("no signing key (verify would return None)", 0, env={"EVIDENCE_SIGNING_KEY": None})
    case("a signing key under 32 characters", 0, env={"EVIDENCE_SIGNING_KEY": "short-key"})
    case("no GitHub token", 0, env={"GH_TOKEN": None, "GITHUB_TOKEN": None})
    case("fetched PR head differs from the event head", 0, lambda d, b, h: {"pull_ref": b})
    # rule 1: change and approval
    case("head branch without a key", 1, ref="feature/login")
    case("head branch with two keys", 1, ref="feature/ABC-7-ABC-8")

    def released_at_base(d):
        vr_state(d, stage="released")
    case("a replayed key whose change is released at the base", 1, fixture=lambda: vr_fixture(base_extra=released_at_base))

    def release_head(d, b, h):
        vr_state(d, stage="released")
        return vr_commit(d, "ABC-7: release")
    case("the change is released at the head", 1, release_head)

    def no_key(d, b, h):
        w(d, "src/app.py", "v = 2\n")
        return vr_commit(d, "tidy up")
    case("a commit without the change key", 1, no_key)

    def no_trailer(d, b, h):
        w(d, "src/app.py", "v = 2\n")
        return vr_commit(d, "ABC-7: more", trailer="")
    case("a commit with neither trailer", 1, no_trailer)
    case("an approving review on a stale SHA", 1,
         lambda d, b, h: {"reviews": [{"user": {"login": "lead"}, "state": "APPROVED", "commit_id": vr_git(d, "git rev-parse HEAD~1")}]})
    case("approval only by the PR author", 1, author="lead")
    case("approval by a non-owner of a changed path", 1, fixture=lambda: vr_fixture(codeowners="* @lead\n/src/ @other\n"))
    case("a team code owner", 1, fixture=lambda: vr_fixture(codeowners="* @org/team\n"))

    def plan_edited(d, b, h):
        w(d, "plan/ABC-7.md", VR_PLAN + "\n3. One more step added after approval.\n")
        return vr_commit(d, "ABC-7: edit plan")
    case("the plan hash differs from approval.json", 1, plan_edited)
    # rule 2: paths
    def evil_merge(d, b, h):
        vr_git(d, f"git checkout -q -b side {b}")
        w(d, "src/side.py", "s = 1\n")
        vr_git(d, "git add -A && git commit -q -m 'ABC-7: side' -m 'Agent-Session: s1'")
        vr_git(d, "git checkout -q feature/ABC-7-login && git merge -q --no-ff --no-commit side")
        w(d, "docs/evil.md", "not claimed\n")
        return vr_commit(d, "ABC-7: merge side")
    case("an evil merge adding an unclaimed path", 2, evil_merge)
    for kind, fn in (("A", lambda d: w(d, "docs/new.md", "x\n")),
                     ("M", lambda d: w(d, "README.md", "changed\n")),
                     ("D", lambda d: os.remove(os.path.join(d, "README.md"))),
                     ("T", lambda d: (os.remove(os.path.join(d, "README.md")), os.symlink("src/app.py", os.path.join(d, "README.md")))),
                     ("R", lambda d: (os.makedirs(os.path.join(d, "lib")), os.rename(os.path.join(d, "src", "app.py"),
                                                                                     os.path.join(d, "lib", "app.py"))))):
        case(f"an unclaimed {kind} path", 2, lambda d, b, h, fn=fn: (fn(d), vr_commit(d, f"ABC-7: unclaimed"))[1])
    # rule 3: secrets and blob size
    secret = "AK" + "IA" + "QWERTYUIOPASDFGH"

    def secret_added_removed(d, b, h):
        w(d, "src/cfg.py", f"key = '{secret}'\n")
        vr_commit(d, "ABC-7: add config")
        os.remove(os.path.join(d, "src", "cfg.py"))
        return vr_commit(d, "ABC-7: remove config")
    case("a secret added then removed", 3, secret_added_removed)

    def big_blob(d, b, h):
        with open(os.path.join(d, "src", "big.bin"), "wb") as f:
            f.write(os.urandom(2 * 1024 * 1024))
        return vr_commit(d, "ABC-7: big")
    case("an oversize blob not on the allow-list", 3, big_blob, org={"verify_range_blob_cap_mb": 1})
    # rule 4: audit logs
    log = os.path.join(".evidence", "audit", "s1.jsonl")

    def truncate_log(d, b, h):
        lines = open(os.path.join(d, log)).read().splitlines(True)
        open(os.path.join(d, log), "w").write("".join(lines[:-1]))
        w(d, "src/app.py", "v = 3\n")
        return vr_commit(d, "ABC-7: truncate", audit=False)
    case("an audit log truncated in a later commit", 4, truncate_log)

    def omitted(d, b, h):
        w(d, "src/app.py", "v = 3\n")
        return vr_commit(d, "ABC-7: other session", session="s2", audit=False)
    case("a named session's log is omitted", 4, omitted)

    def base_log(d):
        with Signed() as s:
            s.st.audit_append(d, "old", {"event": "tool", "key": "ABC-0"})
    case("an audit log that exists at the base is deleted", 4,
         lambda d, b, h: (os.remove(os.path.join(d, ".evidence", "audit", "old.jsonl")), vr_commit(d, "ABC-7: drop log"))[1],
         fixture=lambda: vr_fixture(base_extra=base_log))
    case("an audit log that exists at the base is type-changed", 4,
         lambda d, b, h: (os.remove(os.path.join(d, ".evidence", "audit", "old.jsonl")),
                          os.symlink("s1.jsonl", os.path.join(d, ".evidence", "audit", "old.jsonl")),
                          vr_commit(d, "ABC-7: link log"))[2],
         fixture=lambda: vr_fixture(base_extra=base_log))
    # rule 5: change records
    vpath = ".evidence/changes/ABC-7/violations.json"

    def violations(d, entries):
        with Signed() as s:
            s.st.write_violations(os.path.join(d, vpath), entries, d)

    def rollback(d, b, h):
        violations(d, [{"path": "src/x", "rule": "unclaimed", "open": True}])
        vr_commit(d, "ABC-7: violation")
        violations(d, [])
        return vr_commit(d, "ABC-7: rollback")
    case("an open violation rolled back", 5, rollback)

    def closed_unsigned(d, b, h):
        violations(d, [{"path": "src/x", "rule": "unclaimed", "open": True}])
        vr_commit(d, "ABC-7: violation")
        violations(d, [{"path": "src/x", "rule": "unclaimed", "open": False}])
        return vr_commit(d, "ABC-7: close")
    case("a violation closed without a signed clear", 5, closed_unsigned)

    def regress(d, b, h):
        vr_state(d, stage="approved")
        return vr_commit(d, "ABC-7: regress")
    case("the state stage moves backwards", 5, regress)

    def bad_sig(d, b, h):
        p = os.path.join(d, ".evidence", "changes", "ABC-7", "state.json")
        rec = json.load(open(p))
        rec["tier"] = 2
        json.dump(rec, open(p, "w"))
        return vr_commit(d, "ABC-7: tier")
    case("a state record at the head with an invalid signature", 5, bad_sig)

    def other_change(d):
        vr_state(d, key="ABC-3")
    case("another change's record edited other than by release or clear", 5,
         lambda d, b, h: (vr_state(d, key="ABC-3", stage="implementing", note="edited"), vr_commit(d, "ABC-7: touch ABC-3"))[1],
         fixture=lambda: vr_fixture(base_extra=other_change))
    case("another change's approval added in this PR", 5,
         lambda d, b, h: (vr_state(d, key="ABC-3"), vr_approval(d, key="ABC-3"), vr_commit(d, "ABC-7: approve ABC-3"))[2],
         fixture=lambda: vr_fixture(base_extra=other_change))

    def release_other(d, b, h):  # this branch's own shape: another change's release and cleared violations ride along
        with Signed() as s:
            s.st.save_state(d, "ABC-3", {"key": "ABC-3", "tier": 1, "kind": "feature", "stage": "released"})
            s.st.write_violations(os.path.join(d, ".evidence/changes/ABC-3/violations.json"),
                                  [{"path": "x", "rule": "r", "open": False, "cleared_by": "lead"}], d)
        return vr_commit(d, "ABC-7: release records of ABC-3")
    case("another change's signed release and cleared violations", None, release_other,
         fixture=lambda: vr_fixture(base_extra=other_change))

    # passing shapes
    def main_moved(d, b, h):
        vr_git(d, "git checkout -q main")
        w(d, "docs/other.md", "main moved\n")
        vr_git(d, "git add -A && git commit -q -m 'ABC-9: elsewhere'")
        nb = vr_git(d, "git rev-parse HEAD")
        vr_git(d, "git checkout -q feature/ABC-7-login")
        return {"base": nb}
    case("a clean branch after main moved", None, main_moved)

    def update_branch(d, b, h):
        got = main_moved(d, b, h)
        vr_git(d, "git merge -q --no-ff -m \"Merge branch 'main' into feature/ABC-7-login\" main")
        return dict(got, head=vr_git(d, "git rev-parse HEAD"))
    case("a clean \"Update branch\" merge of main", None, update_branch)

    def human(d, b, h):
        w(d, "src/app.py", "v = 4\n")
        return vr_commit(d, "ABC-7: human fix", trailer="Human-Commit: lead", audit=False)
    case("a human commit with a Human-Commit: trailer and the key", None, human)

    def dispatch(d, b, h):
        return {"event": {"inputs": {"pr": "5"}}, "event_name": "workflow_dispatch"}
    case("a workflow_dispatch re-run with the PR number", None, dispatch)

    # Code review (step 11): the shapes of a real repository, where every merged PR adds records and logs
    def main_gains_records(d, b, h):
        vr_git(d, "git checkout -q main")
        w(d, "plan/ABC-3.md", VR_PLAN.replace("ABC-7", "ABC-3"))
        vr_state(d, key="ABC-3", stage="released")
        vr_approval(d, key="ABC-3", plan="plan/ABC-3.md")
        with Signed() as s:
            s.st.audit_append(d, "m1", {"event": "tool", "key": "ABC-3"})
            s.st.audit_append(d, "clear-violations", {"event": "violations-cleared", "key": "ABC-3"})
        vr_git(d, "git add -A && git commit -q -m 'ABC-3: merged elsewhere' -m 'Agent-Session: m1'")
        nb = vr_git(d, "git rev-parse HEAD")
        vr_git(d, "git checkout -q feature/ABC-7-login")
        return {"base": nb}
    case("a branch not updated after main gained another change's records and logs", None, main_gains_records)

    def update_after_records(d, b, h):
        got = main_gains_records(d, b, h)
        vr_git(d, "git merge -q --no-ff -m \"Merge branch 'main' into feature/ABC-7-login\" main")
        return dict(got, head=vr_git(d, "git rev-parse HEAD"))
    case("an \"Update branch\" merge that brings in another change's records", None, update_after_records)

    def shared_log_both_sides(d, b, h):
        with Signed() as s:
            s.st.audit_append(d, "clear-violations", {"event": "violations-cleared", "key": "ABC-7"})
        vr_commit(d, "ABC-7: clear")
        got = main_gains_records(d, b, h)  # main also appends to clear-violations.jsonl
        subprocess.run("git merge -q --no-commit main", shell=True, cwd=d, env=ENV, capture_output=True)
        ours = vr_git(d, "git show HEAD:.evidence/audit/clear-violations.jsonl")
        theirs = vr_git(d, "git show main:.evidence/audit/clear-violations.jsonl")
        extra = [l for l in theirs.splitlines() if l not in ours.splitlines()]
        w(d, ".evidence/audit/clear-violations.jsonl", ours + "\n" + "\n".join(extra) + "\n")
        return dict(got, head=vr_commit(d, "ABC-7: merge main (shared log appended on both sides)"))
    case("a merge of a shared log both sides appended to", None, shared_log_both_sides,
         fixture=lambda: vr_fixture(base_extra=lambda d: _vr_shared_log(d)))

    # Security review (step 11): shapes that hid from per-commit checks
    def rename_log_away_and_back(d, b, h):
        with Signed() as s:
            s.st.audit_append(d, "old", {"event": "deny", "key": "ABC-0"})
            s.st.audit_append(d, "old", {"event": "integrity-violation", "key": "ABC-0"})
        vr_git(d, "git checkout -q main && git add -A && git commit -q -m 'ABC-0: log'")
        nb = vr_git(d, "git rev-parse HEAD")
        vr_git(d, f"git checkout -q feature/ABC-7-login && git merge -q --no-ff -m \"Merge branch 'main' into feature/ABC-7-login\" main")
        log = os.path.join(d, ".evidence", "audit", "old.jsonl")
        first = open(log).read().splitlines(True)[:1]
        vr_git(d, "git mv .evidence/audit/old.jsonl .evidence/audit/x.jsonl")
        vr_commit(d, "ABC-7: move a log")
        vr_git(d, "git rm -q .evidence/audit/x.jsonl")
        w(d, ".evidence/audit/old.jsonl", "".join(first))  # back, with its tail cut off
        return {"base": nb, "head": vr_commit(d, "ABC-7: put it back")}
    case("an audit log renamed away and added back truncated", 4, rename_log_away_and_back)

    def rename_record_away_and_back(d, b, h):
        vpath = os.path.join(d, ".evidence/changes/ABC-3/violations.json")
        with Signed() as s:
            s.st.write_violations(vpath, [{"path": "x", "rule": "r", "at": "t", "open": True}], d)
        vr_git(d, "git mv .evidence/changes/ABC-3/violations.json .evidence/changes/ABC-3/v.json")
        vr_commit(d, "ABC-7: move a record")
        vr_git(d, "git rm -q .evidence/changes/ABC-3/v.json")
        with Signed() as s:
            s.st.write_violations(vpath, [], d)  # back, without the open violation
        return vr_commit(d, "ABC-7: put it back")

    def open_violation_at_base(d):
        vr_state(d, key="ABC-3")
        with Signed() as s:
            s.st.write_violations(os.path.join(d, ".evidence/changes/ABC-3/violations.json"),
                                  [{"path": "x", "rule": "r", "at": "t", "open": True}], d)
    case("another change's violations renamed away and added back without the open one", 5, rename_record_away_and_back,
         fixture=lambda: vr_fixture(base_extra=open_violation_at_base))

    def old_base_merge(d, b, h):
        m_old = b  # ABC-3 is implementing here
        vr_git(d, "git checkout -q main")
        vr_state(d, key="ABC-3", stage="released")
        vr_git(d, "git add -A && git commit -q -m 'ABC-3: release'")
        nb = vr_git(d, "git rev-parse HEAD")
        vr_git(d, f"git checkout -q feature/ABC-7-login && git merge -q --no-ff -m \"Merge branch 'main' into feature/ABC-7-login\" main")
        subprocess.run(f"git merge -q -s ours --no-commit {m_old}", shell=True, cwd=d, env=ENV, capture_output=True)
        vr_git(d, f"git checkout {m_old} -- .evidence/changes/ABC-3/state.json")
        return {"base": nb, "head": vr_commit(d, "ABC-7: merge an old main commit")}
    case("a crafted merge of an old base commit that rolls back another change's release", 5, old_base_merge,
         fixture=lambda: vr_fixture(base_extra=other_change))

    case("an unclaimed change to .evidence/policy.json", 2,
         lambda d, b, h: (w(d, ".evidence/policy.json", "{\"verify_range_allow_large\": [\"**\"]}\n"),
                          vr_commit(d, "ABC-7: loosen policy"))[1])
    case("a PR that targets another branch than the default", 0,
         lambda d, b, h: {"event": {"pull_request": {"number": 5, "base": {"sha": b, "ref": "develop"},
                                                     "head": {"sha": h, "ref": "feature/ABC-7-login"},
                                                     "user": {"login": "dev"}},
                                    "repository": {"default_branch": "main"}}})

    def copied_approval(d, b, h):
        with Signed() as s:
            rec = s.signing.sign({"key": "ABC-3", "plan_path": "plan/ABC-7.md", "approver": "lead", "method": "github",
                                  "plan_sha256": s.st.sha256_file(os.path.join(d, "plan", "ABC-7.md")),
                                  "approved_at": "2026-09-25T00:00:00Z"})
            s.st.write_file(d, ".evidence/changes/ABC-7/approval.json", json.dumps(rec, indent=2, sort_keys=True) + "\n")
        return vr_commit(d, "ABC-7: approval copied from another change")
    case("an approval record copied from another change", 1, copied_approval)

    # PILOT-62 REQ-LLA-04: rule 5 also judges violation entries that first appear in the range
    def lla04(label, entries, expect_pass, note=None):
        d, b, _ = vr_fixture()
        violations(d, entries)
        h = vr_commit(d, "ABC-7: record")
        r = vr_run(d, b, h)
        out = r.stdout + r.stderr
        ok = r.returncode == 0 if expect_pass else (r.returncode != 0 and "rule 5" in out.lower())
        if note:
            ok = ok and note in out
        check(f"REQ-LLA-04 {label}", ok and "traceback" not in out.lower(), (r.returncode, out[-600:]))
        shutil.rmtree(d)

    base_v = {"at": "2026-09-25T00:00:00Z", "session": "s1"}
    lla04("verify-range: a closed-at-birth restored control-plane entry passes and is printed as a note",
          [dict(base_v, path=".evidence/changes/ABC-7/approval.json", rule="control-plane", action="restored", open=False,
                resolved="restored", resolved_at="2026-09-25T00:00:01Z")], True,
          note="NOTE: .evidence/changes/ABC-7/violations.json: .evidence/changes/ABC-7/approval.json (control-plane) was undone")
    lla04("verify-range: a closed-at-birth removed control-plane-symlink entry passes",
          [dict(base_v, path=".claude/skills/x", rule="control-plane-symlink", action="removed", open=False,
                resolved="restored", resolved_at="2026-09-25T00:00:01Z")], True, note="NOTE")
    lla04("verify-range: a closed-at-birth hidden-change entry without cleared_by fails rule 5",
          [dict(base_v, path="~/.claude.json", rule="hidden-change", action="recorded", open=False)], False)
    lla04("verify-range: a closed-at-birth hidden-change entry claiming resolved=restored fails rule 5",
          [dict(base_v, path="~/.claude.json", rule="hidden-change", action="recorded", open=False, resolved="restored")], False)
    lla04("verify-range: a closed-at-birth control-plane entry that was only recorded (not undone) fails rule 5",
          [dict(base_v, path=".evidence/policy.json", rule="control-plane", action="recorded", open=False,
                resolved="restored")], False)
    lla04("verify-range: a closed-at-birth entry with cleared_by passes (2.1.0 behaviour)",
          [dict(base_v, path="src/x", rule="outside-claims", action="recorded", open=False, cleared_by="lead",
                cleared_at="2026-09-25T00:00:02Z")], True)
    lla04("verify-range: an open entry that first appears passes (it blocks locally, not here)",
          [dict(base_v, path="src/x", rule="outside-claims", action="recorded", open=True)], True)
    # rule 7: push report mode
    d, base, head = vr_fixture()
    w(d, "docs/new.md", "x\n")
    head = vr_commit(d, "ABC-7: unclaimed")
    r = vr_run(d, base, head, event={"before": base, "after": head}, event_name="push", args=["--push-report"])
    check("REQ-IMH-19 push mode reports a failure and never blocks",
          r.returncode == 0 and "docs/new.md" in r.stdout and "rule 2" in r.stdout.lower(), r.stdout[-500:] + r.stderr[-300:])
    r = vr_run(d, base, head, event={"before": "0" * 40, "after": head}, event_name="push", args=["--push-report"])
    check("REQ-IMH-19 push mode skips an all-zero `before` with a note",
          r.returncode == 0 and "skip" in (r.stdout + r.stderr).lower(), r.stdout[-300:] + r.stderr[-300:])
    shutil.rmtree(d)
    verify_range_59_tests()


def verify_range_59_tests():
    """PILOT-59 REQ-CON-17, 18, 19, 21: the verify-range review items (CHANGELOG 2.1.0)."""
    def w(d, rel, text):
        os.makedirs(os.path.dirname(os.path.join(d, rel)) or d, exist_ok=True)
        open(os.path.join(d, rel), "w").write(text)

    def expect(label, r, rule, word=None):
        out = (r.stdout + r.stderr).lower()
        ok = r.returncode == 0 if rule is None else (r.returncode != 0 and f"rule {rule}" in out)
        ok = ok and "traceback" not in out and (word is None or word in out)
        check(label, ok, (r.returncode, r.stdout[-700:] + r.stderr[-300:]))

    def main_appends(d, name, session, n=1):
        """main gains `n` lines on .evidence/audit/<name>.jsonl; returns the new base."""
        vr_git(d, "git checkout -q main")
        with Signed() as s:
            for k in range(n):
                s.st.audit_append(d, session, {"event": "tool", "key": "ABC-3", "n": k})
        vr_git(d, f"git add -A && git commit -q -m 'ABC-3: main appends to {name}' -m 'Agent-Session: {session}'")
        nb = vr_git(d, "git rev-parse HEAD")
        vr_git(d, "git checkout -q feature/ABC-7-login")
        return nb

    def merge_with(d, rel, lines, msg):
        subprocess.run("git merge -q --no-ff --no-commit main", shell=True, cwd=d, env=ENV, capture_output=True)
        w(d, rel, "".join(l + "\n" for l in lines))
        return vr_commit(d, msg, audit=False)

    def lines_at(d, rev, rel):
        return vr_git(d, f"git show {rev}:{rel}").splitlines()

    def old_log(d):
        with Signed() as s:
            s.st.audit_append(d, "old", {"event": "tool", "key": "ABC-0"})

    # REQ-CON-17: containment is ordered, for the whole range and a merge's other parents
    d, b, h = vr_fixture(base_extra=old_log)
    rel = ".evidence/audit/old.jsonl"
    nb = main_appends(d, "old", "old", n=2)
    theirs = lines_at(d, nb, rel)
    head = merge_with(d, rel, [theirs[0], theirs[2], theirs[1]], "ABC-7: merge main, log lines reordered")
    expect("REQ-CON-17 a log whose lines are reordered by a merge fails rule 4", vr_run(d, nb, head), 4)
    shutil.rmtree(d)
    d, b, h = vr_fixture(base_extra=old_log)
    nb = main_appends(d, "old", "old", n=2)
    vr_git(d, "git merge -q --no-ff -m \"Merge branch 'main' into feature/ABC-7-login\" main")
    expect("REQ-CON-17 an append-only range with an update merge passes", vr_run(d, nb, vr_git(d, "git rev-parse HEAD")),
           None)
    shutil.rmtree(d)

    # REQ-CON-18: a shared log merged with the base's lines first passes; a line from neither parent fails
    for label, forge, rule in (("the base's lines first passes", False, None),
                               ("a merged line from neither parent fails rule 4", True, 4)):
        d, b, h = vr_fixture(base_extra=_vr_shared_log)
        rel = ".evidence/audit/clear-violations.jsonl"
        with Signed() as s:
            s.st.audit_append(d, "clear-violations", {"event": "violations-cleared", "key": "ABC-7"})
        vr_commit(d, "ABC-7: clear")
        nb = main_appends(d, "clear-violations", "clear-violations")
        ours, theirs = lines_at(d, "HEAD", rel), lines_at(d, nb, rel)
        merged = theirs + [l for l in ours if l not in theirs] + (['{"event": "forged"}'] if forge else [])
        head = merge_with(d, rel, merged, "ABC-7: merge main (base's lines first)")
        expect(f"REQ-CON-18 shared log merge: {label}", vr_run(d, nb, head), rule)
        shutil.rmtree(d)
    # REQ-CON-18: one session's log appended on both sides fails, and the message says to rebase
    def s1_at_base(d):
        with Signed() as s:
            s.st.audit_append(d, "s1", {"event": "tool", "key": "ABC-0"})
    d, b, h = vr_fixture(base_extra=s1_at_base)
    rel = ".evidence/audit/s1.jsonl"
    nb = main_appends(d, "s1", "s1")
    ours, theirs = lines_at(d, "HEAD", rel), lines_at(d, nb, rel)
    head = merge_with(d, rel, ours + [l for l in theirs if l not in ours], "ABC-7: merge main (s1 on both sides)")
    expect("REQ-CON-18 one session's log appended on both sides of a merge fails rule 4 and says to rebase",
           vr_run(d, nb, head), 4, word="rebase")
    shutil.rmtree(d)

    # REQ-CON-19: only real records and session logs are exempt from claims
    for rel in (".evidence/changes/ABC-7/run.sh", ".evidence/audit/notes.txt", ".evidence/violations/notes.md",
                ".evidence/audit/sub/x.jsonl"):
        d, b, h = vr_fixture()
        w(d, rel, "x\n")
        expect(f"REQ-CON-19 an unclaimed non-record file under .evidence fails rule 2: {rel}",
               vr_run(d, b, vr_commit(d, "ABC-7: extra file")), 2)
        shutil.rmtree(d)
    d, b, h = vr_fixture()
    expect("REQ-CON-19 state.json, approval.json and a session .jsonl stay exempt", vr_run(d, b, h), None)
    shutil.rmtree(d)

    # REQ-CON-21: CODEOWNERS patterns without a slash match at any depth
    sys.path.insert(0, os.path.join(HERE, "..", "engine"))
    import lifecycle
    for pats, path, owned in (("docs @o", "a/b/docs/x.md", True), ("docs/ @o", "a/docs/x.md", True),
                              ("/docs @o", "a/docs/x.md", False), ("/docs @o", "docs/x.md", True),
                              ("src/app.py @o", "x/src/app.py", False), ("src/app.py @o", "src/app.py", True),
                              ("*.js @o", "a/b/c.js", True), ("docs/*.md @o", "a/docs/x.md", False)):
        rules = [(l.split()[0], l.split()[1:]) for l in [pats]]
        got = lifecycle._owners_of(rules, path)
        check(f"REQ-CON-21 CODEOWNERS `{pats}` {'owns' if owned else 'does not own'} {path}", bool(got) == owned, got)


FIX60 = os.path.join(HERE, "fixtures", "pilot60")
SPEC60 = "intent/2026-01-01-x/spec.md"


def _trace():
    """The traceability CLI module, for direct checks of the adapter reader and graph."""
    sys.path.insert(0, os.path.join(HERE, "..", "cli"))
    import evidence_trace
    return evidence_trace


def _junit(path, names):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<testsuite name="fresh" tests="%d" failures="0">\n' % len(names))
        for n in names:
            f.write(f'  <testcase classname="fresh" name="{n} works"></testcase>\n')
        f.write("</testsuite>\n")


def gaps_repo(adapter_extra="", committed=True, plans=(), specs=((SPEC60, "spec.md"),)):
    """A fixture repository for `evidence gaps`: the commented adapter, a spec, one test per
    requirement and (optionally) a committed passing result under the adapter's location."""
    d = os.path.realpath(tempfile.mkdtemp(prefix="evidence-gaps-"))
    os.makedirs(os.path.join(d, ".evidence"))
    shutil.copy(os.path.join(FIX60, "adapter-comments.yml"), os.path.join(d, ".evidence", "adapter.yml"))
    if adapter_extra:
        open(os.path.join(d, ".evidence", "adapter.yml"), "a").write(adapter_extra)
    for rel, src in specs:
        os.makedirs(os.path.join(d, os.path.dirname(rel)), exist_ok=True)
        shutil.copy(os.path.join(FIX60, src), os.path.join(d, rel))
    for rel, src in plans:
        os.makedirs(os.path.join(d, os.path.dirname(rel)), exist_ok=True)
        if src.startswith("#"):
            open(os.path.join(d, rel), "w").write(src)
        else:
            shutil.copy(os.path.join(FIX60, src), os.path.join(d, rel))
    os.makedirs(os.path.join(d, "tests"))
    with open(os.path.join(d, "tests", "test_x.sh"), "w") as f:
        for rid in ("REQ-X-01", "REQ-X-02", "REQ-V2C-09") + (("REQ-Y-01",) if plans else ()):
            f.write(f'check_ok "{rid} works"\n')
    if committed:
        os.makedirs(os.path.join(d, "validation", "results"))
        shutil.copy(os.path.join(FIX60, "pass.xml"), os.path.join(d, "validation", "results", "pass.xml"))
    subprocess.run("git init -q -b main && git add -A && git commit -q -m 'ABC-1: fixture'", shell=True, cwd=d,
                   env=ENV, check=True)
    return d


def gaps_tests():
    """PILOT-60: `evidence gaps --self-check` / `--only-results` (REQ-USA-02, 03), YAML comments in the
    adapter and eval front matter (REQ-USA-05), and plan rows that repeat their spec (REQ-USA-06)."""
    et = _trace()
    from pathlib import Path
    # ---- REQ-USA-02: --self-check exempts only the hard-coded REQ-V2C-09
    d = gaps_repo(committed=False)
    fresh = d + "-fresh"
    _junit(os.path.join(fresh, "r.xml"), ["REQ-X-01", "REQ-X-02"])
    r = run(["gaps", "--strict", "--self-check", "--only-results", "--results", fresh], d)
    check("REQ-USA-02 gaps --strict --self-check passes when only the self-check requirement is unproven, and says so",
          r.returncode == 0 and "self-check: REQ-V2C-09" in r.stdout, r.stdout[-600:] + r.stderr[-300:])
    r = run(["gaps", "--strict", "--only-results", "--results", fresh], d)
    check("REQ-USA-02 without --self-check the unproven self-check requirement still blocks",
          r.returncode == 1 and "REQ-V2C-09" in r.stdout, r.stdout[-600:] + r.stderr[-300:])
    _junit(os.path.join(fresh, "r.xml"), ["REQ-X-01"])
    r = run(["gaps", "--strict", "--self-check", "--only-results", "--results", fresh], d)
    check("REQ-USA-02 --self-check does not exempt another unproven requirement",
          r.returncode == 1 and "REQ-X-02" in r.stdout, r.stdout[-600:] + r.stderr[-300:])
    shutil.rmtree(d)
    shutil.rmtree(fresh)
    d = gaps_repo(adapter_extra="self_check_requirement: REQ-X-02\n", committed=False)
    fresh = d + "-fresh"
    _junit(os.path.join(fresh, "r.xml"), ["REQ-X-01", "REQ-V2C-09"])
    r = run(["gaps", "--strict", "--self-check", "--only-results", "--results", fresh], d)
    check("REQ-USA-02 an adapter self_check_requirement key cannot exempt another requirement",
          r.returncode == 1 and "REQ-X-02" in r.stdout, r.stdout[-600:] + r.stderr[-300:])
    shutil.rmtree(d)
    shutil.rmtree(fresh)

    # ---- REQ-USA-03: --only-results ignores the adapter's committed results
    d = gaps_repo(committed=True)
    fresh = d + "-fresh"
    os.makedirs(fresh)
    r = run(["gaps", "--strict", "--only-results", "--results", fresh], d)
    check("REQ-USA-03 gaps --only-results ignores a committed passing result under test_results_location",
          r.returncode == 1 and "REQ-X-01" in r.stdout, r.stdout[-600:] + r.stderr[-300:])
    r = run(["gaps", "--strict", "--results", fresh], d)
    check("REQ-USA-03 without --only-results the committed result still counts (2.1.0 behaviour)",
          r.returncode == 0, r.stdout[-600:] + r.stderr[-300:])
    r = run(["gaps", "--only-results"], d)
    check("REQ-USA-03 gaps --only-results without --results exits 2 with a message",
          r.returncode == 2 and "--results" in (r.stdout + r.stderr), r.stdout[-300:] + r.stderr[-300:])
    shutil.rmtree(fresh)

    # ---- REQ-USA-05: inline comments are stripped, quoted or unspaced # is kept
    a, _ = et.load_adapter(Path(d))
    check("REQ-USA-05 a commented `- glob   # comment` list item is the bare glob",
          a.get("spec_glob") == ["intent/*/spec.md", "plan/*.md"], a.get("spec_glob"))
    check("REQ-USA-05 a quoted value followed by a comment is unquoted and uncommented",
          a.get("tracker_pattern") == "[A-Z]+-[0-9]+" and a.get("requirement_pattern") == "REQ-[A-Za-z0-9]+-[0-9]+",
          (a.get("tracker_pattern"), a.get("requirement_pattern")))
    check("REQ-USA-05 an inline list followed by a comment is a list",
          a.get("test_results_location") == ["validation/results"] and a.get("test_dir_segments") == ["tests"],
          (a.get("test_results_location"), a.get("test_dir_segments")))
    check("REQ-USA-05 negative: a # inside quotes, or with no space before it, is part of the value",
          a.get("hash_quoted") == "a # not a comment" and a.get("hash_unspaced") == "a#b",
          (a.get("hash_quoted"), a.get("hash_unspaced")))
    check("REQ-USA-05 a nested artifact_chain.plan_glob inline list is read",
          (a.get("artifact_chain") or {}).get("plan_glob") == ["intent/*/plan.md", "plan/*.md"], a.get("artifact_chain"))
    r = run(["gaps"], d)
    check("REQ-USA-05 the commented spec glob finds the spec's requirements",
          "3 requirements from 1 spec file" in r.stdout, r.stdout[:400])
    shutil.rmtree(d)
    rx = __import__("re").compile(r"REQ-[A-Za-z0-9]+-[0-9]+")
    covers = et.find_eval_covers("---\nname: x\ncovers: [REQ-X-01]  # was REQ-X-09\n---\nbody\n", rx)
    check("REQ-USA-05 negative: an eval `covers:` comment is not read as a covered ID", covers == ["REQ-X-01"], covers)
    tmpd = os.path.realpath(tempfile.mkdtemp(prefix="evidence-adapter-"))
    os.makedirs(os.path.join(tmpd, ".evidence"))
    open(os.path.join(tmpd, ".evidence", "adapter.yml"), "w").write("requirement_pattern: 'REQ-#-[0-9]+'\n")
    a2, _ = et.load_adapter(Path(tmpd))
    check("REQ-USA-05 negative: a quoted pattern containing # keeps it", a2.get("requirement_pattern") == "REQ-#-[0-9]+",
          a2.get("requirement_pattern"))
    shutil.rmtree(tmpd)

    # ---- REQ-USA-06: plan rows that repeat their From: spec are references
    def dup(d):
        g = et.build_graph(Path(d), et.load_adapter(Path(d))[0])
        return g, g.get("duplicate_requirements", {})

    d = gaps_repo(plans=(("plan/ABC-1.md", "plan-ref.md"),))
    g, dups = dup(d)
    r = run(["gaps", "--strict"], d)
    check("REQ-USA-06 a plan row repeating its From: spec's ID is a reference, not a DUPLICATE-ID",
          "REQ-X-01" not in dups and g["requirements"].get("REQ-X-01", {}).get("spec_file") == SPEC60
          and "The spec's summary" in g["requirements"].get("REQ-X-01", {}).get("summary", "")
          and "REQ-X-01: defined in" not in r.stdout, (dups, g["requirements"].get("REQ-X-01"), r.stdout[-400:]))
    shutil.rmtree(d)
    d = gaps_repo(plans=(("plan/ABC-1.md", open(os.path.join(FIX60, "plan-ref.md")).read().replace(
        "`intent/2026-01-01-x/spec.md`", "intent/2026-01-01-x/")),))
    check("REQ-USA-06 a plan whose From: names the spec's directory (trailing slash) is a reference",
          "REQ-X-01" not in dup(d)[1], dup(d)[1])
    shutil.rmtree(d)
    d = gaps_repo(plans=(("plan/ABC-2.md", "plan-other.md"),))
    g, dups = dup(d)
    check("REQ-USA-06 negative: the same row in a plan whose From: names another spec is a DUPLICATE-ID",
          "REQ-X-01" in dups, dups)
    shutil.rmtree(d)
    d = gaps_repo(specs=((SPEC60, "spec.md"), ("intent/2026-01-01-z/spec.md", "spec.md")))
    check("REQ-USA-06 negative: two specs defining one ID is a DUPLICATE-ID", "REQ-X-01" in dup(d)[1], dup(d)[1])
    shutil.rmtree(d)
    t1 = "# Plan: t1\nTracker: ABC-3   From: spec.md\nRisk tier: 1\n\n| REQ ID | Requirement |\n| --- | --- |\n| REQ-Y-01 | plan-only |\n"
    d = gaps_repo(plans=(("plan/ABC-3.md", t1), ("plan/ABC-4.md", t1.replace("ABC-3", "ABC-4"))))
    check("REQ-USA-06 negative: two plans defining one plan-only ID is a DUPLICATE-ID", "REQ-Y-01" in dup(d)[1], dup(d)[1])
    shutil.rmtree(d)
    d = gaps_repo(plans=(("plan/ABC-3.md", t1),))
    g, dups = dup(d)
    r = run(["gaps"], d)
    orphan = r.stdout.split("ORPHANED", 1)[1].split("\n\n", 1)[0] if "ORPHANED" in r.stdout else ""
    check("REQ-USA-06 a Tier 1 plan-only ID is defined by the plan, not orphaned",
          "REQ-Y-01" in g["requirements"] and "REQ-Y-01" not in dups and "REQ-Y-01" not in orphan, (dups, orphan))
    shutil.rmtree(d)


def approve_github_59_tests():
    """PILOT-59 REQ-CON-16: a GitHub approval must not come from the change's creator. The creator's
    login comes from the org policy's approval.github_identities (email -> login or [logins])."""
    def setup(tier, identities, repo_policy=None, author="bot"):
        d = repo()
        subprocess.run("git config user.email dev@x.com", shell=True, cwd=d, env=ENV, check=True)
        org = {"unsigned_max_tier": 3, "approval": {"github_repo": "o/r"}}
        if identities is not None:
            org["approval"]["github_identities"] = identities
        org_path = os.path.join(d, ".git", "org.json")
        json.dump(org, open(org_path, "w"))
        env = {"EVIDENCE_ORG_POLICY": org_path}
        os.makedirs(os.path.join(d, "plan"))
        os.makedirs(os.path.join(d, "intent", "ABC-7"))
        open(os.path.join(d, "plan", "ABC-7.md"), "w").write(PLAN.replace("Risk tier: 1", f"Risk tier: {tier}"))
        open(os.path.join(d, "intent", "ABC-7", "intent.md"), "w").write("# Intent\nTracker: ABC-7\n")
        open(os.path.join(d, "intent", "ABC-7", "spec.md"), "w").write("# Spec\nTracker: ABC-7\n")
        extra = ["--intent", "intent/ABC-7/intent.md", "--spec", "intent/ABC-7/spec.md"] if tier >= 2 else []
        r = run(["change", "start", "ABC-7", "--tier", str(tier), "--kind", "feature", "--plan", "plan/ABC-7.md"] + extra,
                d, env=env)
        assert r.returncode == 0, r.stderr
        if repo_policy is not None:
            json.dump(repo_policy, open(os.path.join(d, ".evidence", "policy.json"), "w"))
        return d, env

    def approve(d, env, reviewer, author="bot"):
        fake = os.path.join(d, ".git", "fake-gh")
        plan_b64 = __import__("base64").b64encode(open(os.path.join(d, "plan", "ABC-7.md"), "rb").read()).decode()
        open(fake, "w").write("#!/bin/bash\n"
                              "case \"$*\" in\n"
                              "  'pr view 5 '*) echo '{\"number\":5,\"headRefName\":\"feature/ABC-7-x\",\"headRefOid\":\"abc\","
                              f"\"url\":\"u\",\"author\":{{\"login\":\"{author}\"}},"
                              f"\"reviews\":[{{\"author\":{{\"login\":\"{reviewer}\"}},\"state\":\"APPROVED\"}}],\"comments\":[]}}';;\n"
                              f"  'api repos/o/r/contents/plan/ABC-7.md?ref=abc') echo '{{\"content\":\"{plan_b64}\"}}';;\n"
                              "  *) exit 1;;\n"
                              "esac\n")
        os.chmod(fake, 0o755)
        return run(["approve", "ABC-7", "--github-pr", "5"], d, env=dict(env, EVIDENCE_GH=fake))

    ap = lambda d: os.path.join(d, ".evidence", "changes", "ABC-7", "approval.json")
    d, env = setup(3, {"dev@x.com": "alice"})
    r = approve(d, env, "alice")
    check("REQ-CON-16 a GitHub approval by the change's creator (org map) is refused",
          r.returncode != 0 and not os.path.isfile(ap(d)) and "creat" in (r.stdout + r.stderr).lower(), r.stdout + r.stderr)
    r = approve(d, env, "Bob")
    rec = json.load(open(ap(d))) if os.path.isfile(ap(d)) else {}
    check("REQ-CON-16 another approver is accepted and creator_login is recorded",
          r.returncode == 0 and rec.get("approver") == "Bob" and rec.get("creator_login") == "alice",
          (r.stdout + r.stderr, rec))
    shutil.rmtree(d)
    d, env = setup(3, {"dev@x.com": ["alice", "alice-work"]})
    r = approve(d, env, "ALICE-work")
    check("REQ-CON-16 any of the creator's logins (case-insensitive) is refused",
          r.returncode != 0 and not os.path.isfile(ap(d)), r.stdout + r.stderr)
    shutil.rmtree(d)
    d, env = setup(3, None, repo_policy={"approval": {"github_identities": {"dev@x.com": "zed"}}})
    r = approve(d, env, "bob")
    check("REQ-CON-16 Tier 3 with no creator login in the org policy is refused (a repository policy cannot supply one)",
          r.returncode != 0 and not os.path.isfile(ap(d)) and "github_identities" in (r.stdout + r.stderr), r.stdout + r.stderr)
    shutil.rmtree(d)
    d, env = setup(1, None)
    r = approve(d, env, "bob")
    check("REQ-CON-16 Tier 1 with no creator login is accepted, with a note",
          r.returncode == 0 and os.path.isfile(ap(d)) and "github_identities" in (r.stdout + r.stderr), r.stdout + r.stderr)
    shutil.rmtree(d)


def fix_base_59_test():
    """PILOT-59 REQ-CON-23: a fix_base git could not read is refused, never recorded empty (which would switch
    test-weakening protection off)."""
    d = os.path.realpath(tempfile.mkdtemp(prefix="evidence-life-"))
    subprocess.run("git init -q -b feature/ABC-9-fix", shell=True, cwd=d, env=ENV, check=True)  # unborn: no HEAD
    run(["change", "start", "ABC-9", "--tier", "1", "--kind", "fix", "--plan", "plan/ABC-9.md"], d)
    os.makedirs(os.path.join(d, "plan"))
    open(os.path.join(d, "plan", "ABC-9.md"), "w").write(PLAN.replace("ABC-7", "ABC-9"))
    s9 = json.loads(run(["change", "status", "ABC-9", "--json"], d).stdout)
    prompt(d, f"evidence approve ABC-9 {s9['plan_sha256'][:12]}")
    r = run(["change", "advance", "ABC-9", "failing-test"], d)
    st9 = json.load(open(os.path.join(d, ".evidence/changes/ABC-9/state.json")))
    check("REQ-CON-23 failing-test is refused when git cannot read HEAD, and no empty fix_base is recorded",
          r.returncode != 0 and "fix_base" not in st9 and st9.get("stage") != "failing-test",
          (r.returncode, r.stdout + r.stderr, st9.get("stage"), st9.get("fix_base")))
    shutil.rmtree(d)


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
    ap8 = os.path.join(d, ".evidence/changes/ABC-8/approval.json")
    # PILOT-58 REQ-IMH-24: gh is pinned to the policy's repository; with none, nothing is asked of gh
    r = run(["approve", "ABC-8", "--github-pr", "5"], d, env={"EVIDENCE_GH": fake, "CLAUDECODE": "1"})
    check("REQ-IMH-24 GitHub approval without a pinned github_repo is refused, never resolved by gh",
          r.returncode != 0 and "github_repo" in (r.stdout + r.stderr) and not os.path.isfile(ap8), r.stdout + r.stderr)
    json.dump({"approval": {"github_repo": "o/r"}}, open(os.path.join(d, ".evidence", "policy.json"), "w"))
    r = run(["approve", "ABC-8", "--github-pr", "5"], d, env={"EVIDENCE_GH": fake, "CLAUDECODE": "1"})
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
    approve_github_59_tests()
    fix_base_59_test()
    signed_terminal_tests()
    verify_range_tests()
    gaps_tests()
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
    if sys.argv[1:] == ["verify-range"]:  # just the REQ-IMH-19 fixtures
        verify_range_tests()
        print(f"\n{res['pass']} passed, {res['fail']} failed")
        sys.exit(1 if res["fail"] else 0)
    if sys.argv[1:] == ["gaps"]:  # just the PILOT-60 gaps fixtures
        gaps_tests()
        print(f"\n{res['pass']} passed, {res['fail']} failed")
        sys.exit(1 if res["fail"] else 0)
    sys.exit(main())
