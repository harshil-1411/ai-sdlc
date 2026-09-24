"""Repository context shared by the gate engine and the `evidence` CLI.

Policy loading and merging, per-change lifecycle state, human approval records,
plan parsing (claims), and the hash-chained audit log. Standard library only.
"""
import datetime as _dt
import fnmatch
import hashlib
import json
import os
import re
import subprocess

ENGINE_VERSION = "2.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_POLICY = os.path.join(HERE, "..", "..", "policy", "default-policy.json")
ORG_POLICY_PATHS = [
    "/Library/Application Support/ClaudeCode/evidence-policy.json",
    "/etc/claude-code/evidence-policy.json",
    r"C:\Program Files\ClaudeCode\evidence-policy.json",
]
STAGES = ["intent", "spec", "plan", "approved", "implementing", "failing-test", "verified", "released"]
TIER_REQUIRED = {1: ["plan"], 2: ["spec", "plan"], 3: ["intent", "spec", "plan"]}


# ------------------------------------------------------------------ helpers

def now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git(args, cwd, timeout=10):
    try:
        out = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def repo_root(cwd):
    out = git(["rev-parse", "--show-toplevel"], cwd)
    if out:
        return os.path.realpath(out.strip())
    return os.path.realpath(cwd)


def current_branch(root):
    out = git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    b = out.strip() if out else ""
    return "" if b == "HEAD" else b


_GLOB_CACHE = {}


def glob_to_regex(pattern, icase=False):
    key = (pattern, icase)
    if key in _GLOB_CACHE:
        return _GLOB_CACHE[key]
    p = pattern.strip()
    anchored = p.startswith("/")
    p = p.lstrip("/")
    if p.endswith("/"):
        p += "**"
    i, out = 0, ""
    while i < len(p):
        c = p[i]
        if c == "*":
            if p[i:i + 3] == "**/":
                out += "(?:.*/)?"
                i += 3
                continue
            if p[i:i + 2] == "**":
                out += ".*"
                i += 2
                continue
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c == "[":
            j = p.find("]", i)
            if j == -1:
                out += re.escape(c)
            else:
                out += "[" + p[i + 1:j].replace("\\", "\\\\") + "]"
                i = j
        else:
            out += re.escape(c)
        i += 1
    # A pattern without a slash matches at any depth (gitignore semantics).
    if not anchored and "/" not in pattern.strip().rstrip("/"):
        out = "(?:.*/)?" + out
    rx = re.compile("^" + out + "$", re.I if icase else 0)
    _GLOB_CACHE[key] = rx
    return rx


def glob_match(path, patterns, icase=False):
    for pat in patterns or []:
        if glob_to_regex(pat, icase).match(path):
            return pat
    return None


# ------------------------------------------------------------------ policy

TIGHTEN_UNION = {"protected_refs", "control_plane", "change_controlled", "test_globs",
                 "prod_words", "read_only_agents", "non_key_prefixes", "deny_git_config_keys",
                 "user_control_plane"}
TIGHTEN_OR = {"enforce_claims", "require_agent_trailer", "deny_agent_merge",
              "require_review_agents", "deny_tier3_auto_modes", "deny_opaque_writes",
              "scan_secrets", "treat_unknown_deploy_target_as_production"}


def _merge(base, over, tighten_only):
    out = dict(base)
    for k, v in over.items():
        if k.startswith("_"):
            continue
        if tighten_only and k in TIGHTEN_UNION and isinstance(v, list):
            out[k] = list(dict.fromkeys(list(base.get(k, [])) + v))
        elif tighten_only and k in TIGHTEN_OR and isinstance(v, bool):
            out[k] = bool(base.get(k, False)) or v
        elif tighten_only and k == "ungated":
            # A repository may narrow what is ungated, never widen it, unless the
            # organisation policy explicitly allows repo additions.
            if base.get("allow_repo_ungated_additions"):
                out[k] = list(dict.fromkeys(list(base.get(k, [])) + v))
            else:
                out[k] = [g for g in v if g in base.get(k, [])]
        elif tighten_only and k == "tier_floors" and isinstance(v, dict):
            merged = dict(base.get(k, {}))
            for g, t in v.items():
                merged[g] = max(int(t), int(merged.get(g, 0)))
            out[k] = merged
        elif tighten_only and k == "required_agents" and isinstance(v, dict):
            merged = {t: list(a) for t, a in base.get(k, {}).items()}
            for t, agents in v.items():
                merged[t] = list(dict.fromkeys(merged.get(t, []) + agents))
            out[k] = merged
        elif tighten_only and k == "approval" and isinstance(v, dict):
            # A repository may move approval from local to github mode (stricter) and add
            # allowed approvers only if the org has listed none; it can never loosen.
            merged = dict(base.get(k, {}))
            if v.get("mode") == "github":
                merged["mode"] = "github"
            if v.get("github_repo") and not merged.get("github_repo"):
                merged["github_repo"] = v["github_repo"]
            if v.get("github_allowed_approvers") and not merged.get("github_allowed_approvers"):
                merged["github_allowed_approvers"] = list(v["github_allowed_approvers"])
            out[k] = merged
        elif tighten_only and k == "key_pattern":
            # descriptive (which tracker this repository uses), but it must still look
            # like a key: a pattern that matches ordinary words would make the commit
            # key check meaningless.
            try:
                rx = re.compile(v)
                if not any(rx.fullmatch(w) for w in ("fix", "wip", "update", "", "UTF-8x", "misc")) and re.search(r"\d", v + "0-9"):
                    out[k] = v
            except re.error:
                pass
        elif tighten_only:
            # Every other key from a repo policy is a potential loosening
            # (change_ticket_pattern, release_approval_pattern, prod_words, ...) and is ignored.
            continue
        else:
            out[k] = v
    return out


def load_policy(root):
    with open(DEFAULT_POLICY) as f:
        policy = json.load(f)
    sources = ["default"]
    # A managed org policy file (deployed by the platform team) wins over the env var,
    # so a developer cannot point the session at a looser policy of their own.
    org_path = next((p for p in ORG_POLICY_PATHS if os.path.isfile(p)), None) or os.environ.get("EVIDENCE_ORG_POLICY")
    if org_path and os.path.isfile(org_path):
        with open(org_path) as f:
            policy = _merge(policy, json.load(f), tighten_only=False)
        sources.append(org_path)
    repo_path = os.path.join(root, ".evidence", "policy.json")
    if os.path.isfile(repo_path):
        with open(repo_path) as f:
            policy = _merge(policy, json.load(f), tighten_only=True)
        sources.append(".evidence/policy.json")
    env_pat = os.environ.get("EVIDENCE_ISSUE_KEY_PATTERN")
    if env_pat and not any(p != "default" for p in sources[1:2] if p != ".evidence/policy.json"):
        policy["key_pattern"] = env_pat
    policy["_sources"] = sources
    return policy


# ------------------------------------------------------------------ keys

def find_keys(text, policy):
    rx = re.compile(policy["key_pattern"])
    keys = []
    for m in rx.finditer(text or ""):
        k = m.group(0)
        prefix = re.split(r"[-_]", k, 1)[0].upper()
        if prefix in {p.upper() for p in policy.get("non_key_prefixes", [])}:
            continue
        keys.append(k)
    return keys


def active_key(root, policy, branch=None):
    env = os.environ.get("EVIDENCE_ACTIVE_CHANGE")
    if env:
        return env.strip(), "EVIDENCE_ACTIVE_CHANGE"
    branch = current_branch(root) if branch is None else branch
    if not branch and any(os.environ.get(v) for v in ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "BUILDKITE", "JENKINS_URL")):
        for var in ("GITHUB_HEAD_REF", "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME", "CI_COMMIT_REF_NAME",
                    "BUILDKITE_BRANCH", "BRANCH_NAME", "GIT_BRANCH"):
            if os.environ.get(var):
                branch = os.environ[var]
                break
    keys = find_keys(branch, policy)
    if keys:
        return keys[0], f"branch {branch}"
    return None, f"branch {branch or '(none)'}"


# ------------------------------------------------------------------ change state

def change_dir(root, key):
    return os.path.join(root, ".evidence", "changes", key)


def load_state(root, key):
    p = os.path.join(change_dir(root, key), "state.json")
    if not os.path.isfile(p):
        return None
    with open(p) as f:
        return json.load(f)


def save_state(root, key, state):
    import signing
    state = signing.sign(dict(state))
    d = change_dir(root, key)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, ".state.json.tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, os.path.join(d, "state.json"))


def load_approval(root, key):
    p = os.path.join(change_dir(root, key), "approval.json")
    if not os.path.isfile(p):
        return None
    with open(p) as f:
        return json.load(f)


def approval_problem(root, key, approval, plan_path):
    """None if the approval is valid for the current plan; else the reason."""
    import signing
    if not approval:
        return "not-approved"
    if approval.get("key") != key:
        return "approval belongs to another change"
    if approval.get("plan_sha256") != sha256_file(plan_path):
        return "approval-stale"
    if signing.verify(approval) is False:
        return "approval signature missing or invalid"
    return None


def find_artifact(root, key, name, state=None):
    """Locate intent.md / spec.md / plan.md for a change."""
    if state and state.get(name):
        p = os.path.join(root, state[name])
        return p if os.path.isfile(p) else None
    candidates = []
    if name == "plan":
        candidates.append(os.path.join(root, "plan", f"{key}.md"))
    intent_dir = os.path.join(root, "intent")
    if os.path.isdir(intent_dir):
        for d in sorted(os.listdir(intent_dir)):
            p = os.path.join(intent_dir, d, f"{name}.md")
            if os.path.isfile(p):
                try:
                    head = open(p, encoding="utf-8", errors="replace").read(2000)
                except OSError:
                    continue
                if re.search(r"Tracker:\s*" + re.escape(key) + r"\b", head):
                    candidates.append(p)
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


_STUB_MARKERS = re.compile(r"<Real, verified paths only|<Every path this plan is going to touch|<One glob per line", re.M)


def plan_problems(plan_path):
    """Return a list of reasons a plan does not count as a real plan."""
    try:
        text = open(plan_path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ["plan file cannot be read"]
    problems = []
    if len(text.strip()) < 200:
        problems.append("plan is empty or a stub")
    claims = plan_claims(text)
    if not claims:
        problems.append('plan has no entries under "## Files claimed"')
    if not section(text, "Order of work").strip():
        problems.append('plan has no "## Order of work"')
    if _STUB_MARKERS.search(section(text, "Files claimed")):
        problems.append('"## Files claimed" still contains template placeholder text')
    return problems


def section(text, heading):
    m = re.search(r"^##\s+" + re.escape(heading) + r"[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def plan_claims(text):
    body = section(text, "Files claimed")
    claims = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith(("-", "*")):
            continue
        ticks = re.findall(r"`([^`]+)`", line)
        if ticks:
            for t in ticks:
                t = t.strip()
                if t and not t.startswith("<") and " " not in t:
                    claims.append(t[2:] if t.startswith("./") else t)
        else:
            tok = line.lstrip("-* ").split()[0] if line.lstrip("-* ") else ""
            if tok and ("/" in tok or "." in tok) and not tok.startswith("<"):
                tok = tok.strip(",;")
                claims.append(tok[2:] if tok.startswith("./") else tok)
    # Expand brace alternatives like {a,b}
    out = []
    for c in claims:
        m = re.search(r"\{([^{}]+)\}", c)
        if m:
            for alt in m.group(1).split(","):
                out.append(c[:m.start()] + alt.strip() + c[m.end():])
        else:
            out.append(c)
    return [re.sub(r"\s*\(new[^)]*\)$", "", c) for c in out]


def claim_matches(path, claims):
    for c in claims:
        c2 = c.rstrip("/")
        if path == c2 or path.startswith(c2 + "/"):
            return c
        if any(ch in c for ch in "*?[") and glob_to_regex("/" + c if not c.startswith("/") else c).match(path):
            return c
    return None


def required_artifacts(tier):
    return TIER_REQUIRED.get(int(tier or 1), ["plan"])


# ------------------------------------------------------------------ violations

def violations_path(root, key, branch):
    if key:
        return os.path.join(change_dir(root, key), "violations.json")
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", branch or "detached")
    return os.path.join(root, ".evidence", "violations", f"{safe}.json")


def record_violations(root, key, state, branch, violations, session):
    p = violations_path(root, key if state else None, branch)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    data = _read_violations(p)
    for v in violations:
        data.append(dict(v, at=now(), session=session, open=True))
    write_violations(p, data)


def _read_violations(p):
    import signing
    if not os.path.isfile(p):
        return []
    try:
        raw = json.load(open(p))
    except ValueError:
        return [{"path": p, "rule": "unreadable violations file", "open": True}]
    if isinstance(raw, list):  # pre-v2.0 format
        return raw
    if signing.verify(raw) is False:
        return [{"path": p, "rule": "violations record altered (signature invalid)", "open": True}]
    return raw.get("entries", [])


def write_violations(p, data):
    import signing
    with open(p, "w") as f:
        json.dump(signing.sign({"entries": data}), f, indent=2)
        f.write("\n")


def open_violations(root, key, branch):
    out = []
    for p in {violations_path(root, key, branch), violations_path(root, None, branch)}:
        out += [v for v in _read_violations(p) if v.get("open")]
    return out


# ------------------------------------------------------------------ audit log

def audit_dir(root):
    return os.path.join(root, ".evidence", "audit")


def _last_hash(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 8192))
            tail = f.read().decode("utf-8", "replace").strip().splitlines()
        if tail:
            return json.loads(tail[-1]).get("hash", "")
    except (OSError, ValueError):
        pass
    return ""


def entry_hash(entry, prev):
    body = {k: v for k, v in entry.items() if k not in ("hash", "sig")}
    body["prev"] = prev
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def audit_append(root, session, entry):
    d = audit_dir(root)
    os.makedirs(d, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session or "unknown")[:80] or "unknown"
    path = os.path.join(d, f"{safe}.jsonl")
    prev = _last_hash(path)
    entry = dict(entry)
    entry.setdefault("ts", now())
    entry.setdefault("session", session)
    entry.setdefault("user", os.environ.get("USER") or os.environ.get("USERNAME") or "unknown")
    entry["prev"] = prev
    entry["hash"] = entry_hash(entry, prev)
    import signing
    entry = signing.sign(entry)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def audit_verify(path):
    """Return (ok, problems). With a signing key configured, every entry must carry a valid signature."""
    import signing
    problems, prev = [], ""
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                problems.append(f"line {n}: not JSON")
                prev = ""
                continue
            if e.get("prev", "") != prev:
                problems.append(f"line {n}: chain broken (prev does not match line {n - 1})")
            if entry_hash(e, e.get("prev", "")) != e.get("hash"):
                problems.append(f"line {n}: content altered (hash mismatch)")
            if signing.verify(e) is False:
                problems.append(f"line {n}: signature missing or invalid (entry not written by the gate engine)")
            prev = e.get("hash", "")
    return not problems, problems


def audit_events(root, predicate=None):
    d = audit_dir(root)
    if not os.path.isdir(d):
        return
    for name in sorted(os.listdir(d)):
        if not name.endswith(".jsonl"):
            continue
        with open(os.path.join(d, name), encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                if predicate is None or predicate(e):
                    yield e


TRUSTED_AGENT_PLUGINS = ("evidence-sdlc", "evidence-quality", "evidence-compliance", "evidence-discovery",
                         "evidence-integrations")


def recorded_agents(root, key):
    """Review agents recorded as completed for a change. Only Evidence Chain's own
    plugin agents (or an unprefixed agent, which can only come from the user's or the
    project's .claude/agents/ -- control plane) count; a same-named agent from any
    other plugin does not satisfy the review gate."""
    import signing
    # A review only counts if it completed after the latest source change for this key:
    # a verifier that ran before later edits proves nothing about them.
    last_write = ""
    for e in audit_events(root, lambda e: e.get("key") == key and e.get("event") == "tool" and e.get("gated")):
        last_write = max(last_write, e.get("ts", ""))
    done = set()
    for e in audit_events(root, lambda e: e.get("event") == "agent-completed" and e.get("key") == key):
        if signing.verify(e) is False:
            continue  # a key is configured and this entry was not signed with it: forged
        if e.get("ts", "") < last_write:
            continue
        t = e.get("subagent_type") or ""
        plugin, _, name = t.rpartition(":")
        if not plugin or plugin in TRUSTED_AGENT_PLUGINS:
            done.add(name or t)
    return done


# ------------------------------------------------------------------ paths

def normalize(path, cwd, root):
    """Return (repo_relative_path or None, absolute_real_path)."""
    if not path:
        return None, None
    p = os.path.expanduser(path)
    if not os.path.isabs(p):
        p = os.path.join(cwd, p)
    # realpath resolves `..` and symlinks of existing prefixes
    real = os.path.realpath(p)
    root_real = os.path.realpath(root)
    if real == root_real:
        return "", real
    if real.startswith(root_real + os.sep):
        return os.path.relpath(real, root_real).replace(os.sep, "/"), real
    return None, real


def is_test_path(rel, policy):
    return bool(glob_match(rel, policy.get("test_globs", []), icase=True))


def file_in_commit(root, commit, rel):
    if not commit:
        return False
    return git(["cat-file", "-e", f"{commit}:{rel}"], root) is not None
