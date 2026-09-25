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
import sys

ENGINE_VERSION = "2.0.1"
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


# ------------------------------------------------------------------ child processes (ADR-0003)
# Hooks hold the signing key and run git in a repository the agent shapes. Every engine
# git or gh process starts here: command-executing config neutralised, and neither GIT_*
# nor the key in its environment.

GIT_NEUTRAL = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "core.pager=cat",
               "-c", "core.attributesFile=/dev/null", "-c", "diff.external=", "-c", "protocol.ext.allow=never",
               "-c", "submodule.recurse=false"]
_NO_SUBMODULES = {"status", "diff"}
_NO_DRIVERS = {"diff", "log", "show"}
_NO_CONFIG_CHECK = {"rev-parse", "config", "version"}  # these run no configured commands
_EMPTY_TREE = {"sha1": "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
               "sha256": "6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321"}


def _child_env():
    """The environment for any process the engine starts: no GIT_* (config, index, object
    and directory overrides) and no signing key."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "EVIDENCE_SIGNING_KEY"}


def _git_argv(args):
    sub = args[:1]
    extra = []
    if sub and sub[0] in _NO_SUBMODULES:
        extra.append("--ignore-submodules=all")
    if sub and sub[0] in _NO_DRIVERS:
        extra += ["--no-ext-diff", "--no-textconv"]
    return ["git"] + GIT_NEUTRAL + sub + extra + list(args[1:])


_ATTR_SOURCE = {}


def _attr_source(cwd):
    """The empty tree, so attributes (diff drivers, filters) come from nowhere the agent can write."""
    key = os.path.realpath(cwd)
    if key not in _ATTR_SOURCE:
        fmt = (run_git(["rev-parse", "--show-object-format"], cwd, _attrs=False) or "").strip()
        _ATTR_SOURCE[key] = _EMPTY_TREE.get(fmt)
    return _ATTR_SOURCE[key]


def run_git(args, cwd, timeout=10, text=True, raise_timeout=False, _attrs=True):
    """Run git with ADR-0003's neutralisation. Returns stdout, or None when git fails, times
    out (unless raise_timeout) or the repository's config is refused (check_git_config).
    None never means "nothing to check": callers on a security path fail closed on it."""
    if args[:1] and args[0] not in _NO_CONFIG_CHECK and check_git_config(cwd):
        return None
    env = _child_env()
    tree = _attr_source(cwd) if _attrs else None
    if tree:
        env["GIT_ATTR_SOURCE"] = tree
    try:
        out = subprocess.run(_git_argv(args), cwd=cwd, env=env, capture_output=True, text=text, timeout=timeout)
    except subprocess.TimeoutExpired:
        if raise_timeout:
            raise
        return None
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def git(args, cwd, timeout=10):
    return run_git(args, cwd, timeout=timeout)


_CONFIG_REFUSAL = {}


def check_git_config(cwd, policy=None):
    """ADR-0003 §2. None if the configuration git would apply here is acceptable, otherwise
    the reason it is refused. A key in the deny set is refused at every scope except
    `command` (the engine's own -c), except `credential.*` at global or system scope; an
    exact key=value from the org's git_allowed_config passes when it has no newline or CR.
    Checked once per process; the race with a concurrent change is ADR-0003 §4."""
    key = os.path.realpath(cwd)
    if key in _CONFIG_REFUSAL:
        return _CONFIG_REFUSAL[key]
    if policy is None:
        policy = load_policy(repo_root(cwd))
    deny = [g.lower() for g in policy.get("deny_git_config_keys", [])]
    allowed = {(e.partition("=")[0].lower(), e.partition("=")[2]) for e in policy.get("git_allowed_config", [])}
    reason = None
    out = run_git(["config", "--list", "-z", "--show-scope", "--show-origin", "--includes"], cwd, text=False)
    if out is None:
        reason = "git could not read its configuration here (run `git config --list` to see why)"
    else:
        fields = out.decode("utf-8", "replace").split("\0")
        for i in range(0, len(fields) - 2, 3):
            scope, origin, kv = fields[i], fields[i + 1], fields[i + 2]
            k, _, v = kv.partition("\n")
            kl = k.lower()
            if scope == "command" or not any(fnmatch.fnmatch(kl, g) for g in deny):
                continue
            if kl.startswith("credential.") and scope in ("global", "system"):
                continue
            if (kl, v) in allowed and "\n" not in v and "\r" not in v:
                continue
            reason = (f"git config {k} ({scope}, {origin}) can make git run a command, and the gate engine runs git "
                      f"with the signing key. A human removes it, or the organisation allow-lists the exact value in "
                      f"the org policy's git_allowed_config")
            break
    _CONFIG_REFUSAL[key] = reason
    return reason


def run_gh(args, cwd, repo, timeout=60):
    """Run gh against the pinned repository only (never whatever `gh repo view` resolves),
    without GIT_* or the key. Raises RuntimeError on refusal or failure."""
    if not repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise RuntimeError("no pinned GitHub repository (policy approval.github_repo, or $GITHUB_REPOSITORY in CI); "
                           "refusing to let gh pick one")
    if args[:1] == ["api"]:
        # gh api takes no --repo: the endpoint itself must name the pinned repository
        path = next((a for a in args[1:] if not a.startswith("-")), "")
        if not path.lstrip("/").startswith(f"repos/{repo}/"):
            raise RuntimeError(f"gh api {path} is outside the pinned repository {repo}")
        argv = list(args)
    else:
        argv = list(args) + ["--repo", repo]
    exe = os.environ.get("EVIDENCE_GH", "gh")
    r = subprocess.run([exe] + argv, cwd=cwd, env=_child_env(), capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"gh {' '.join(argv)} failed")
    return r.stdout


def git_marker_above(path):
    """True if a .git entry exists at or above path: a repository, whether or not git can read it."""
    d = os.path.realpath(path or ".")
    while True:
        if os.path.lexists(os.path.join(d, ".git")):
            return True
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent


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

SAFE_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}")


def change_dir(root, key):
    # A key becomes a path component; the unsandboxed hook writes here, so no `/`, `..` or absolute keys.
    if not SAFE_KEY.fullmatch(key or ""):
        raise ValueError(f"'{key}' is not a usable change key (letters, digits, '-' and '_' only)")
    return os.path.join(root, ".evidence", "changes", key)


def load_state(root, key):
    p = os.path.join(change_dir(root, key), "state.json")
    if not os.path.isfile(p):
        return None
    with open(p) as f:
        state = json.load(f)
    if isinstance(state, dict) and state.get("key") not in (None, key):
        # a signed state copied under another key's directory
        raise ValueError(f"{p} belongs to change {state.get('key')}, not {key}")
    return state


# ------------------------------------------------------------------ engine writes
# Hooks run outside the agent's sandbox and hold the signing key, so every file the engine
# writes is reached through directory handles opened without following symlinks: a link the
# agent's shell planted under .evidence/ (or anywhere on the path) cannot redirect the write.

def _rel_parts(rel):
    parts = rel.replace(os.sep, "/").split("/")
    if not parts or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"refusing engine write to '{rel}'")
    return parts


def _dir_fd(root, dirs, create=True):
    """A handle on root/dirs..., creating missing directories; refuses any symlinked component."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for d in dirs:
            try:
                nfd = os.open(d, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(d, 0o755, dir_fd=fd)
                except FileExistsError:
                    pass  # a concurrent call created it first
                nfd = os.open(d, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nfd
        return fd
    except BaseException:
        os.close(fd)
        raise


def write_file(root, rel, data):
    """Replace root/rel atomically with data (str or bytes). A fresh O_EXCL temp file is renamed
    over the target, so neither a symlink nor a hard link at the target or temp name is followed."""
    parts = _rel_parts(rel)
    dfd = _dir_fd(root, parts[:-1])
    tmp = f".{parts[-1]}.{os.getpid()}.tmp"
    try:
        try:
            os.unlink(tmp, dir_fd=dfd)
        except FileNotFoundError:
            pass
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=dfd)
        with os.fdopen(fd, "wb") as f:
            f.write(data.encode() if isinstance(data, str) else data)
        os.replace(tmp, parts[-1], src_dir_fd=dfd, dst_dir_fd=dfd)
    finally:
        os.close(dfd)


def remove_file(root, rel):
    """Unlink root/rel through directory handles: a symlinked component raises, and a symlink
    at rel itself is removed, never what it points to. A directory is refused (OSError)."""
    parts = _rel_parts(rel)
    dfd = _dir_fd(root, parts[:-1], create=False)
    try:
        os.unlink(parts[-1], dir_fd=dfd)
    finally:
        os.close(dfd)


def read_file_nofollow(root, rel, cap):
    """Bytes of root/rel, read without following a link anywhere on the path. Raises OSError
    for a link, a non-regular file or more than `cap` bytes."""
    import stat
    parts = _rel_parts(rel)
    dfd = _dir_fd(root, parts[:-1], create=False)
    try:
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=dfd)
    finally:
        os.close(dfd)
    with os.fdopen(fd, "rb") as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode):
            raise OSError(f"{rel} is not a regular file")
        if s.st_size > cap:
            raise OSError(f"{rel} is larger than {cap} bytes")
        data = f.read(cap + 1)
    if len(data) > cap:
        raise OSError(f"{rel} is larger than {cap} bytes")
    return data


def open_append(root, rel):
    """root/rel opened for reading and appending (binary). Refuses a symlink, a non-regular file
    and a file with other hard links, which could point outside the repository."""
    import stat
    parts = _rel_parts(rel)
    for attempt in range(5):
        dfd = _dir_fd(root, parts[:-1])
        try:
            fd = os.open(parts[-1], os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o644, dir_fd=dfd)
            break
        except FileNotFoundError:
            # seen on macOS when concurrent first calls are still creating the directory; walk again
            if attempt == 4:
                raise
        finally:
            os.close(dfd)
    st_ = os.fstat(fd)
    if not stat.S_ISREG(st_.st_mode) or st_.st_nlink != 1:
        os.close(fd)
        raise ValueError(f"refusing to append to '{rel}': not a plain file")
    return os.fdopen(fd, "a+b")


def save_state(root, key, state):
    import signing
    state = signing.sign(dict(state))
    change_dir(root, key)  # validates the key
    write_file(root, f".evidence/changes/{key}/state.json", json.dumps(state, indent=2, sort_keys=True) + "\n")


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
    data = _read_violations(p)
    for v in violations:
        data.append(dict(v, at=now(), session=session, open=True))
    write_violations(p, data, root)


def _read_violations(p):
    import signing
    import stat
    try:
        mode = os.lstat(p).st_mode
    except FileNotFoundError:
        return []
    except OSError as e:
        return [{"path": p, "rule": f"violations record unreadable ({e.strerror})", "open": True}]
    if not stat.S_ISREG(mode):
        # a directory, link or other non-file here must not read as "no violations" (REQ-IMH-02)
        return [{"path": p, "rule": "violations record is not a regular file", "open": True}]
    try:
        raw = json.load(open(p))
    except OSError as e:
        return [{"path": p, "rule": f"violations record unreadable ({e.strerror})", "open": True}]
    except ValueError:
        return [{"path": p, "rule": "unreadable violations file", "open": True}]
    if isinstance(raw, list):  # pre-v2.0 format: trusted only when no key is deployed
        if signing.enabled():
            return [{"path": p, "rule": "violations record in unsigned legacy format", "open": True}]
        return raw
    if signing.verify(raw) is False:
        return [{"path": p, "rule": "violations record altered (signature invalid)", "open": True}]
    return raw.get("entries", [])


def write_violations(p, data, root):
    import signing
    write_file(root, os.path.relpath(p, root), json.dumps(signing.sign({"entries": data}), indent=2) + "\n")


def open_violations(root, key, branch):
    out = []
    for p in {violations_path(root, key, branch), violations_path(root, None, branch)}:
        out += [v for v in _read_violations(p) if v.get("open")]
    return out


# ------------------------------------------------------------------ audit log

def audit_dir(root):
    return os.path.join(root, ".evidence", "audit")


def entry_hash(entry, prev):
    body = {k: v for k, v in entry.items() if k not in ("hash", "sig")}
    body["prev"] = prev
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _last_hash_fd(f):
    try:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - 8192))
        tail = f.read().decode("utf-8", "replace").strip().splitlines()
        if tail:
            return json.loads(tail[-1]).get("hash", "")
    except (OSError, ValueError):
        pass
    return ""


def _open_log(root, rel, session):
    """The session log for appending. A log the engine cannot append to (hard-linked, made read-only,
    replaced by something that is not a file) is moved aside -- kept as evidence -- and a fresh log is
    started whose first entry says so, with a violation recorded. Raises if even that is impossible."""
    try:
        return open_append(root, rel)
    except (OSError, ValueError) as e:
        # Only the log itself being refused is tampering; anything else (a directory problem, a race)
        # is raised, never "recovered" by moving a healthy log aside.
        import errno
        if not os.path.lexists(os.path.join(root, rel)) or (
                isinstance(e, OSError) and e.errno not in (errno.EACCES, errno.EPERM, errno.ELOOP, errno.EISDIR,
                                                           errno.ENXIO, errno.EMLINK)):
            raise
        import secrets
        import signing
        parts = _rel_parts(rel)
        dfd = _dir_fd(root, parts[:-1])
        aside = f"{parts[-1]}.unwritable-{secrets.token_hex(4)}"
        try:
            os.rename(parts[-1], aside, src_dir_fd=dfd, dst_dir_fd=dfd)
        finally:
            os.close(dfd)
        f = open_append(root, rel)
        first = {"event": "audit-log-replaced", "reason": str(e)[:200], "moved_to": aside, "ts": now(), "session": session,
                 "prev": ""}
        first["hash"] = entry_hash(first, "")
        f.write((json.dumps(signing.sign(first), sort_keys=True) + "\n").encode())
        f.flush()
        try:
            record_violations(root, None, None, current_branch(root), [{"path": rel, "rule": "audit-tamper",
                                                                         "action": f"moved aside to {aside}"}], session)
        except Exception:
            pass  # the replacement entry above is the record
        return f


def audit_ready(root, session):
    """Raise if this session's existing audit log cannot be appended to (after recovery)."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session or "unknown")[:80] or "unknown"
    rel = f".evidence/audit/{safe}.jsonl"
    try:
        os.lstat(os.path.join(root, ".evidence"))
    except FileNotFoundError:
        return  # this repository keeps no evidence yet; nothing to protect
    # Proven by opening (creating) the log itself, not with exists(), which reads "cannot look" as
    # "absent", and not by entering the directory, which a read-only directory still allows.
    _open_log(root, rel, session).close()


def audit_append(root, session, entry):
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session or "unknown")[:80] or "unknown"
    entry = dict(entry)
    entry.setdefault("ts", now())
    entry.setdefault("session", session)
    entry.setdefault("user", os.environ.get("USER") or os.environ.get("USERNAME") or "unknown")
    import signing
    with _open_log(root, f".evidence/audit/{safe}.jsonl", session) as f:
        # Concurrent tool calls (parallel subagents) append to the same log: read the last
        # hash and append under one exclusive lock, or two entries share a prev and the chain forks.
        try:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX)
        except (ImportError, OSError) as e:
            sys.stderr.write(f"evidence: audit log lock unavailable ({e}); concurrent calls may fork the chain\n")
        prev = _last_hash_fd(f)
        entry["prev"] = prev
        entry["hash"] = entry_hash(entry, prev)
        entry = signing.sign(entry)
        f.write((json.dumps(entry, sort_keys=True) + "\n").encode())
        f.flush()
    return entry


def audit_verify(path, warnings=None):
    """Return (ok, problems). With a signing key configured, every entry must carry a valid signature.

    A fork -- an entry whose prev is its predecessor's prev, i.e. two entries appended from the
    same last hash by concurrent calls before appends were locked -- is not a break: both are
    hash-correct (and signed), and nothing is missing. It is reported in `warnings`. A deleted,
    altered or reordered entry still fails, because some prev then matches neither neighbour.

    An entry hash seen earlier in the log is a replay, and in a session log (<session>.jsonl) every
    entry must belong to that session; the approval and clear-violations logs are shared by name
    (REQ-IMH-11)."""
    import signing
    problems, prev, prev_of_prev, prev_session, first_session = [], "", None, None, None
    seen = set()
    name = os.path.basename(path)
    shared = not name.endswith(".jsonl") or name.startswith("approval-") or name == "clear-violations.jsonl"
    stem = name[:-len(".jsonl")]
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                problems.append(f"line {n}: not JSON")
                prev, prev_of_prev = "", None
                continue
            first_session = first_session if n > 1 else e.get("session")
            if e.get("prev", "") != prev:
                # a fork is two different entries of this log's own session appended from one
                # predecessor -- not a duplicate of its sibling, not another session's chain spliced in
                if (prev_of_prev is not None and e.get("prev", "") == prev_of_prev and e.get("hash") != prev
                        and e.get("session") == prev_session == first_session):
                    if warnings is not None:
                        warnings.append(f"line {n}: fork (appended concurrently with line {n - 1} from the same entry)")
                else:
                    problems.append(f"line {n}: chain broken (prev does not match line {n - 1})")
            if entry_hash(e, e.get("prev", "")) != e.get("hash"):
                problems.append(f"line {n}: content altered (hash mismatch)")
            if signing.verify(e) is False:
                problems.append(f"line {n}: signature missing or invalid (entry not written by the gate engine)")
            if e.get("hash") in seen:
                problems.append(f"line {n}: replayed (an earlier line has the same entry hash)")
            seen.add(e.get("hash"))
            if not shared:
                own = re.sub(r"[^A-Za-z0-9_-]", "_", str(e.get("session") or "unknown"))[:80] or "unknown"
                if own != stem:
                    problems.append(f"line {n}: entry of session {e.get('session')!r} in the log of {stem!r}")
            prev, prev_of_prev, prev_session = e.get("hash", ""), e.get("prev", ""), e.get("session")
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
    """True if rel exists in commit. Callers deny on True, so a git failure answers True (REQ-IMH-23)."""
    if not commit:
        return False
    out = git(["ls-tree", "--name-only", commit, "--", rel], root)
    return out is None or bool(out.strip())
