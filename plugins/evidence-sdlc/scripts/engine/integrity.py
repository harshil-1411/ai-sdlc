"""Integrity monitor: catches writes the Bash parser could not see.

The PreToolUse parser only understands programs it knows. Any other program
(a compiled binary, awk's system(), make, an npm script) can write files it never
saw. So around every allowed Bash call:

  pre  -- snapshot: content of every existing control-plane file, and a hash of
          every dirty or untracked file in the working tree (git status)
  post -- compare. A control-plane change is reverted from the snapshot; when the
          revert is verified (re-read equals the snapshot, or the path is gone) the
          violation is recorded closed at birth, within a per-session cap (PILOT-62).
          Any other changed file is judged as if it had been an Edit; a write the gates
          would have denied becomes an open violation, and push/PR stay blocked until a
          human reviews and clears it (`evidence change clear-violations`).

Detection, not prevention -- the difference from the pre-check is stated plainly in
SECURITY.md. Standard library only.
"""
import base64
import glob
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile

import state as st

MAX_HASH_BYTES = 8 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 4 * 1024 * 1024
# Audit logs are hashed on every Bash call. Past this size a log is not read at all: the
# monitor could not finish inside the hook's time limit, so the log is refused instead.
AUDIT_LOG_CAP = 64 * 1024 * 1024
# (rule, action) pairs the monitor can undo and verify; only these may be closed at birth
# (REQ-LLA-01) and accepted closed by verify-range rule 5 (REQ-LLA-04).
AUTO_RESOLVABLE = frozenset({("control-plane", "restored"), ("control-plane", "removed"),
                             ("control-plane-symlink", "removed")})


def oversize_audit_logs(root):
    """Audit log names over AUDIT_LOG_CAP, by lstat only (a sparse file costs nothing to make)."""
    d = st.audit_dir(root)
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return out
    for n in sorted(names):
        try:
            if os.lstat(os.path.join(d, n)).st_size > AUDIT_LOG_CAP:
                out.append(n)
        except OSError:
            pass
    return out


def _snap_rel(session, tool_use_id):
    """The snapshot's path relative to the temp dir. Written and read only through st's
    no-follow helpers, so a link planted in the shared temp dir redirects nothing."""
    return "/".join(("evidence-chain-snapshots", re.sub(r"[^A-Za-z0-9_-]", "_", session or "s"),
                     re.sub(r"[^A-Za-z0-9_-]", "_", tool_use_id or "last") + ".json"))


def _snap_path(session, tool_use_id):
    return os.path.join(tempfile.gettempdir(), _snap_rel(session, tool_use_id))


def _static_prefix(pat):
    parts = pat.strip("/").split("/")
    static = []
    for c in parts:
        if any(ch in c for ch in "*?["):
            break
        static.append(c)
    return static, len(static) == len(parts)


def _control_plane_entries(root, policy):
    """(files, odd): regular control-plane files, and the symlinks or non-files found at a
    control-plane path or under a control-plane directory. Nothing here follows a link, so a
    symlinked directory is reported, never walked into (REQ-IMH-01)."""
    pats = policy.get("control_plane", [])
    files, odd, prefixes = set(), set(), set()

    def kind(rel):
        try:
            return os.lstat(os.path.join(root, rel)).st_mode
        except OSError:
            return None

    def linked_component(comps):
        for i in range(1, len(comps) + 1):
            m = kind("/".join(comps[:i]))
            if m is not None and stat.S_ISLNK(m):
                return "/".join(comps[:i])
        return None

    for pat in pats:
        static, literal = _static_prefix(pat)
        if not literal:
            prefixes.add("/".join(static))
            continue
        link = linked_component(static[:-1]) if len(static) > 1 else None
        if link:
            odd.add(link)
            continue
        m = kind("/".join(static))
        if m is None:
            continue
        if stat.S_ISREG(m):
            files.add("/".join(static))
        else:
            odd.add("/".join(static))
    for pre in sorted(prefixes):
        comps = pre.split("/") if pre else []
        link = linked_component(comps)
        if link:
            odd.add(link)
            continue
        m = kind(pre) if pre else stat.S_IFDIR
        if m is None or not stat.S_ISDIR(m):
            continue
        for dp, dns, fns in os.walk(os.path.join(root, pre) if pre else root, followlinks=False):
            reld = os.path.relpath(dp, root)
            reld = "" if reld == "." else reld
            # glob semantics: `**` does not enter or match dot-entries
            dns[:] = [d for d in dns if not d.startswith(".")]
            for n in dns + fns:
                if n.startswith("."):
                    continue
                rel = f"{reld}/{n}" if reld else n
                m = kind(rel)
                if m is None or stat.S_ISDIR(m):
                    continue
                matched = st.glob_match(rel, pats)
                if stat.S_ISREG(m):
                    if matched:
                        files.add(rel)
                elif matched or (pre and stat.S_ISLNK(m)):
                    # under an engine-owned directory any link is suspect; repository-wide
                    # patterns (**/x) only care about a link at a matching name
                    odd.add(rel)
    return sorted(files), sorted(odd)


def _control_plane_files(root, policy):
    return _control_plane_entries(root, policy)[0]


def _read_cp(root, rel):
    """Current content of a control-plane file, or None if it is absent or not a regular file."""
    try:
        return base64.b64encode(st.read_file_nofollow(root, rel, MAX_HASH_BYTES)).decode()
    except (OSError, ValueError):
        return None


PERMISSION_FILE = ".claude/settings.local.json"


LOCAL_SETTINGS_KEPT_KEYS = ["model", "outputStyle"]
_ABSENT = object()


def _local_settings_change(old_b64, cur_b64, pol=None):
    """How a change to settings.local.json made during a call is judged, by effect (REQ-LLA-05):
    ("grant", added) when the only difference is new permissions.allow entries (the B4 case);
    ("kept", summary) when every difference is an allow entry added or removed, a deny or ask
    entry added, an additionalDirectories entry removed, or a top-level key listed in
    local_settings_kept_keys; None for anything else, which is restored. Strict UTF-8, no BOM.
    A newly created file (old_b64 None) is kept only when its whole content is permissions.allow
    entries (the 2.1.0 B4 grant); any other new file is removed like any created control-plane file."""
    pol = pol or {}
    try:
        # strict UTF-8 with no BOM: json.loads also takes UTF-16/32, which Claude Code may not read
        old = json.loads(base64.b64decode(old_b64).decode("utf-8")) if old_b64 else {}
        raw = base64.b64decode(cur_b64)
        if raw.startswith(b"\xef\xbb\xbf"):
            return None
        new = json.loads(raw.decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    if not isinstance(old, dict) or not isinstance(new, dict):
        return None
    if old_b64 is None:
        perms = new.get("permissions")
        allow = perms.get("allow") if isinstance(perms, dict) else None
        if (set(new) == {"permissions"} and set(perms) == {"allow"} and isinstance(allow, list) and allow
                and all(isinstance(x, str) for x in allow)):
            return ("grant", list(dict.fromkeys(allow)))
        return None
    kept_keys = pol.get("local_settings_kept_keys", LOCAL_SETTINGS_KEPT_KEYS)
    kept_keys = [k for k in kept_keys if isinstance(k, str) and k != "permissions"] if isinstance(kept_keys, list) else []
    summary = {}
    for k in sorted(set(old) | set(new)):
        if k == "permissions" or old.get(k, _ABSENT) == new.get(k, _ABSENT):
            continue
        if k not in kept_keys:
            return None
        summary.setdefault("keys", []).append(k)
    op, np_ = old.get("permissions", {}), new.get("permissions", {})
    if not isinstance(op, dict) or not isinstance(np_, dict):
        return None
    # sub-key -> (additions allowed, removals allowed)
    # additionalDirectories additions widen what the agent's tools may reach, so only removals are kept
    rules = {"allow": (True, True), "deny": (True, False), "ask": (True, False), "additionalDirectories": (False, True)}
    for k in sorted(set(op) | set(np_)):
        a, b = op.get(k, _ABSENT), np_.get(k, _ABSENT)
        if a == b:
            continue
        if k not in rules:
            return None  # defaultMode, disableBypassPermissionsMode and anything unknown: restored
        a = [] if a is _ABSENT else a
        b = [] if b is _ABSENT else b
        if not isinstance(a, list) or not isinstance(b, list) or not all(isinstance(x, str) for x in a + b):
            return None
        added, removed = [x for x in b if x not in a], [x for x in a if x not in b]
        can_add, can_remove = rules[k]
        if (added and not can_add) or (removed and not can_remove):
            return None
        if added:
            summary[f"{k}_added"] = added[:20]
        if removed:
            summary[f"{k}_removed"] = removed[:20]
    if set(summary) == {"allow_added"}:
        return ("grant", summary["allow_added"])
    return ("kept", summary)



def _permission_grant(old_b64, cur_b64):
    """The allow rules added, if the only difference is new permissions.allow entries (2.1.0 B4)."""
    got = _local_settings_change(old_b64, cur_b64, {"local_settings_kept_keys": []})
    return got[1] if got and got[0] == "grant" else None


def _not_user_writable(path):
    """True when the session's user could not have written `path` (REQ-LLA-06): it is not a link,
    it is not owned by this uid, and neither it nor its parent directory is writable by this uid.
    A path that does not exist is judged by its parent directory alone. Any error: False."""
    try:
        uid = os.getuid()
        parent = os.path.dirname(path) or "/"
        ps = os.stat(parent)
        if ps.st_uid == uid or os.access(parent, os.W_OK):
            return False
        try:
            s = os.lstat(path)
        except FileNotFoundError:
            return True
        if stat.S_ISLNK(s.st_mode) or s.st_uid == uid or os.access(path, os.W_OK):
            return False
        return True
    except (OSError, AttributeError):
        return False


CLAUDE_JSON_SECURITY_KEYS = ["mcpServers", "allowedTools", "enabledMcpjsonServers", "disabledMcpjsonServers",
                             "enableAllProjectMcpServers"]
CLAUDE_JSON_CAP = 64 * 1024 * 1024


def _claude_json_projection(path, keys=None):
    """sha256 of the security-relevant part of ~/.claude.json (REQ-LLA-07): the top-level
    mcpServers and, under projects.*, the listed keys. Claude Code's own bookkeeping (counters,
    caches, tips, costs) is left out. A missing, oversize or unparsable file has its own marker."""
    keys = [k for k in (keys if isinstance(keys, list) else CLAUDE_JSON_SECURITY_KEYS) if isinstance(k, str)]
    try:
        s = os.lstat(path)
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unreadable"
    if not stat.S_ISREG(s.st_mode):
        return "not-a-file"
    if s.st_size > CLAUDE_JSON_CAP:
        return "oversize"
    try:
        with open(path, "rb") as f:
            data = json.loads(f.read(CLAUDE_JSON_CAP + 1).decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return "invalid"
    if not isinstance(data, dict):
        return "invalid"
    proj = {"mcpServers": data.get("mcpServers")}
    projects = data.get("projects")
    if projects is not None and not isinstance(projects, dict):
        return "invalid"
    per = {}
    for p, v in sorted((projects or {}).items()):
        if not isinstance(v, dict):
            continue
        sel = {k: v[k] for k in keys if k in v}
        if sel:
            per[p] = sel
    proj["projects"] = per
    return "proj:" + hashlib.sha256(json.dumps(proj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


USER_CONFIG_NOT_CHARGED = [
    "/Library/Application Support/ClaudeCode/managed-settings.json",
    "/Library/Application Support/ClaudeCode/managed-settings.d/**",
    "/Library/Application Support/ClaudeCode/evidence-policy.json",
    "/etc/claude-code/managed-settings.json",
    "/etc/claude-code/managed-settings.d/**",
    "/etc/claude-code/evidence-policy.json",
]


def _listed(path, pats):
    """True if `path` (absolute) matches one of the ~-expanded patterns; `/**` covers a subtree."""
    import fnmatch
    for pat in pats if isinstance(pats, list) else []:
        if not isinstance(pat, str):
            continue
        p = os.path.expanduser(pat)
        if p.endswith("/**"):
            if path.startswith(p[:-2]):
                return True
        elif fnmatch.fnmatchcase(path, p):
            return True
    return False


def _claude_json_paths(policy):
    """~/.claude.json (and $CLAUDE_CONFIG_DIR/.claude.json when that is set) when the user control
    plane lists ~/.claude.json: judged by its security projection, not its bytes (REQ-LLA-07)."""
    if "~/.claude.json" not in (policy.get("user_control_plane") or []):
        return []
    out = [os.path.expanduser("~/.claude.json")]
    cdir = os.environ.get("CLAUDE_CONFIG_DIR")
    if cdir:
        out.append(os.path.join(os.path.expanduser(cdir), ".claude.json"))
    return list(dict.fromkeys(out))


def _extra_change(k, b, a, policy):
    """How one user-level entry changed between the snapshot (b) and now (a): None (no change that
    counts), "user-config" (a system file the session's user could not write, REQ-LLA-06) or
    "hidden" (a hidden-change violation)."""
    if b == a:
        return None
    proj_b, proj_a = isinstance(b, dict) and "proj" in b, isinstance(a, dict) and "proj" in a
    if proj_b or proj_a:
        if proj_a and (b is None or proj_b):
            was = b.get("proj") if proj_b else "missing"  # absent from a snapshot: not there
            return None if was == a.get("proj") else "hidden"
        if proj_a and isinstance(b, str):  # a 2.1.x snapshot: whole-file hash, as before
            return None if os.path.isfile(k) and b == _hash(k) else "hidden"
        return "hidden"
    if isinstance(b, str) or isinstance(a, str):
        bh = b.get("h") if isinstance(b, dict) else b
        ah = a.get("h") if isinstance(a, dict) else a
        if bh == ah:
            return None
        if not (isinstance(b, dict) or isinstance(a, dict)):
            return "hidden"
    if _listed(k, policy.get("user_config_not_charged", USER_CONFIG_NOT_CHARGED)):
        if (b is None or isinstance(b, dict)) and (a is None or isinstance(a, dict)):
            b_sys = b.get("sys") if isinstance(b, dict) else _not_user_writable(k)
            a_sys = a.get("sys") if isinstance(a, dict) else _not_user_writable(k)
            if b_sys is True and a_sys is True:
                return "user-config"
    return "hidden"


def _git_dir_id(root):
    gd = (st.run_git(["rev-parse", "--absolute-git-dir"], root) or "").strip()
    try:
        s = os.lstat(gd) if gd else None
    except OSError:
        s = None
    return [gd, s.st_dev, s.st_ino] if s else None


def _hash(path):
    try:
        if os.path.getsize(path) > MAX_HASH_BYTES:
            st_ = os.stat(path)
            return f"size:{st_.st_size}:mtime:{st_.st_mtime_ns}"
        return st.sha256_file(path)
    except OSError:
        return None


def _is_git(root):
    return st.run_git(["rev-parse", "--git-dir"], root) is not None


def _dirty(root):
    # --untracked-files=normal collapses untracked directories, which keeps this fast on
    # large repositories (a new file in an untracked directory shows as the directory).
    try:
        out = st.run_git(["status", "--porcelain=v1", "-z", "--untracked-files=normal"], root, timeout=20, text=False,
                         raise_timeout=True)
    except subprocess.TimeoutExpired:
        return "timeout"
    if out is None:
        return None
    files = {}
    parts = out.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(parts):
        entry = parts[i]
        if len(entry) < 4:
            i += 1
            continue
        code, path = entry[:2], entry[3:]
        if code[0] in "RC":
            i += 1  # rename/copy: next field is the source path
        full = os.path.join(root, path)
        if os.path.isdir(full):
            # One entry per file, keyed like a staged file, so staging or unstaging a file
            # (which moves it in and out of a collapsed directory entry) is not a change.
            for dp, _, fns in os.walk(full):
                for fn in sorted(fns)[:2000]:
                    files[os.path.relpath(os.path.join(dp, fn), root)] = _hash(os.path.join(dp, fn))
        else:
            files[path] = _hash(full) if os.path.isfile(full) else None
        i += 1
    return files


def cli_writes(ctx):
    """Control-plane files the `evidence` CLI legitimately writes for this command, when
    the command consists only of evidence CLI calls (and harmless shell glue)."""
    import cmdparse
    cmd = ctx.tool_input.get("command") or ""
    simples, ok, _ = cmdparse.split_simple(cmd)
    allowed = set()
    for s in simples:
        if s.prog in ("cd", "echo", "true", "printf"):
            continue
        is_cli = s.prog == "evidence" or (s.prog.startswith("python") and len(s.argv) > 1
                                          and os.path.basename(s.argv[1]) == "evidence")
        if not is_cli:
            return set()
        args = [a for a in s.argv[1:] if not a.startswith("-")]
        if s.prog != "evidence":
            args = args[1:]
        # `change start|advance` never reach the shell: the hook performs them (hook.lifecycle_decision).
        if args[:1] == ["approve"] and len(args) > 1 and any(a.startswith("--github-pr") for a in s.argv):
            allowed.update({f".evidence/changes/{args[1]}/approval.json", f".evidence/changes/{args[1]}/state.json"})
    return allowed


def snapshot(ctx):
    import signing
    root, pol = ctx.root, ctx.policy
    if not _is_git(root):
        return
    cp = {}
    files, odd = _control_plane_entries(root, pol)
    for rel in files:
        if rel.startswith(".evidence/audit/"):
            continue  # the audit log legitimately grows on every call
        try:
            data = st.read_file_nofollow(root, rel, MAX_HASH_BYTES)
            cp[rel] = base64.b64encode(data).decode()
        except OSError:
            cp[rel] = None  # present but too large (or unreadable) to restore: still tracked
    dirty = _dirty(root)
    snap = {"cp": cp, "odd": odd, "dirty": dirty if isinstance(dirty, dict) else {}, "timeout": dirty == "timeout",
            "tool_use_id": ctx.payload.get("tool_use_id") or "last", "session": ctx.session, "taken_at": st.now(),
            "audit": _audit_prefixes(root), "cli_writes": sorted(cli_writes(ctx)), "root": root, "extras": _extras(root, pol),
            "git_dir": _git_dir_id(root), "dirs": _dir_ids(root)}
    st.write_file(tempfile.gettempdir(), _snap_rel(ctx.session, ctx.payload.get("tool_use_id")),
                  json.dumps(signing.sign(snap)))


def _extras(root, policy):
    """Things `git status` does not show that can still change what gets reviewed:
    git hooks/config/excludes, index flags that hide working-tree edits, the set of
    ignored top-level entries, and the user-level control plane."""
    ex = {}
    gd = (st.run_git(["rev-parse", "--git-dir"], root) or "").strip()
    gd = gd if os.path.isabs(gd) else os.path.join(root, gd)
    for rel in ("config", "info/exclude", "info/attributes"):
        p = os.path.join(gd, rel)
        ex[f".git/{rel}"] = _hash(p) if os.path.isfile(p) else None
    hooks = os.path.join(gd, "hooks")
    if os.path.isdir(hooks):
        for n in sorted(os.listdir(hooks)):
            if not n.endswith(".sample"):
                ex[f".git/hooks/{n}"] = _hash(os.path.join(hooks, n))
    try:
        flags = st.run_git(["ls-files", "-v"], root, timeout=20, raise_timeout=True)
        hidden = sorted(l[2:] for l in (flags or "").splitlines() if l[:1].islower() or l[:1] == "S")
        ex["(index flags)"] = hashlib.sha256("\n".join(hidden).encode()).hexdigest() if flags is not None else "git-failed"
        ign = st.run_git(["status", "--porcelain", "--ignored=matching", "--untracked-files=no"], root, timeout=20,
                         raise_timeout=True)
        ex["(ignored entries)"] = (hashlib.sha256("\n".join(sorted(l for l in ign.splitlines() if l.startswith("!!"))).encode()).hexdigest()
                                   if ign is not None else "git-failed")
    except subprocess.TimeoutExpired:
        ex["(index flags)"] = "timeout"
    cj = _claude_json_paths(policy)
    not_charged = policy.get("user_config_not_charged", USER_CONFIG_NOT_CHARGED)
    for pat in list(policy.get("user_control_plane", [])) + ["~/.gitconfig", "~/.config/git/config", "~/.claude/CLAUDE.md"]:
        p = os.path.expanduser(pat)
        for f in (glob.glob(p, recursive=True)[:500] if "*" in p else [p]):
            if f in cj:
                continue
            if os.path.isfile(f):
                # a listed system file also records whether the session's user could have written it
                ex[f] = {"h": _hash(f), "sys": _not_user_writable(f)} if _listed(f, not_charged) else _hash(f)
    for f in cj:
        ex[f] = {"proj": _claude_json_projection(f, policy.get("claude_json_security_keys"))}
    return ex


EVIDENCE_DIRS = (".evidence", ".evidence/audit", ".evidence/changes", ".evidence/violations")


def _dir_ids(root):
    """Type, mode, owner and identity of the .evidence directories (REQ-IMH-05): a chmod or a
    swapped directory changes what the engine can write or what a later read sees."""
    out = {}
    for rel in EVIDENCE_DIRS:
        try:
            s = os.lstat(os.path.join(root, rel))
            out[rel] = [stat.S_IFMT(s.st_mode), stat.S_IMODE(s.st_mode), s.st_uid, s.st_dev, s.st_ino]
        except OSError:
            out[rel] = None
    return out


def _audit_prefixes(root):
    """{log name: [size, sha256 of those bytes]} for each regular audit log (REQ-IMH-20)."""
    d = st.audit_dir(root)
    out = {}
    try:
        names = os.listdir(d)
    except OSError:
        return out
    for n in names:
        h = _prefix_hash(root, f".evidence/audit/{n}", None)
        if h:
            out[n] = h
    return out


def _prefix_hash(root, rel, size):
    """[size, sha256] of the first `size` bytes (all of it when None) of a regular file read
    without following links; None if it is not a regular file or is shorter than `size`."""
    try:
        parts = st._rel_parts(rel)
        dfd = st._dir_fd(root, parts[:-1], create=False)
        try:
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0), dir_fd=dfd)
        finally:
            os.close(dfd)
        with os.fdopen(fd, "rb") as f:
            s = os.fstat(f.fileno())
            if not stat.S_ISREG(s.st_mode):
                return None
            want = s.st_size if size is None else size
            if s.st_size < want:
                return None
            if want > AUDIT_LOG_CAP:
                return ["oversize", want]
            h, left = hashlib.sha256(), want
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    return None
                h.update(chunk)
                left -= len(chunk)
            return [want, h.hexdigest()]
    except (OSError, ValueError):
        return None


def check(ctx, judge):
    """Compare against the pre-snapshot. `judge(rel)` returns a deny Decision or None.
    Returns (notes, violations)."""
    import signing
    root, pol = ctx.root, ctx.policy
    tmp, srel = tempfile.gettempdir(), _snap_rel(ctx.session, ctx.payload.get("tool_use_id"))
    git_ok = _is_git(root)
    if not os.path.lexists(os.path.join(tmp, srel)):
        if not git_ok and not st.git_marker_above(root):
            return [], [], []  # no repository before the call (pre snapshots every call in one), none now
        # pre always snapshots an allowed Bash call in a git repo; a missing snapshot means
        # something removed it, so what the command did cannot be checked.
        return (["the integrity snapshot for that command is missing, so its effects could not be checked."],
                [{"path": "(integrity snapshot)", "rule": "integrity-snapshot-missing", "action": "recorded"}], [])
    try:
        snap = json.loads(st.read_file_nofollow(tmp, srel, MAX_SNAPSHOT_BYTES))
        if not isinstance(snap, dict):
            raise ValueError("not an object")
    except (OSError, ValueError) as e:
        # a link, a non-file, an oversize or unparsable snapshot is an altered one (REQ-IMH-08)
        snap = None
        why = str(e)[:120]
    finally:
        try:
            st.remove_file(tmp, srel)
        except OSError:
            pass
    if snap is None:
        return ([f"the integrity snapshot for that command was altered ({why}), so its effects could not be checked."],
                [{"path": "(integrity snapshot)", "rule": "integrity-snapshot-altered", "action": "recorded"}], [])
    notes, violations, changed_gated = [], [], []
    if snap.get("tool_use_id") != (ctx.payload.get("tool_use_id") or "last") or snap.get("session") != ctx.session:
        notes.append("the integrity snapshot for that command belongs to a different command (replayed), so its effects could not be checked.")
        return notes, [{"path": "(integrity snapshot)", "rule": "integrity-snapshot-replayed", "action": "recorded"}], []
    if signing.verify(snap) is False:
        notes.append("the integrity snapshot for that command was altered, so its effects could not be checked.")
        violations.append({"path": "(integrity snapshot)", "rule": "integrity-snapshot-altered", "action": "recorded"})
        return notes, violations, []
    if snap.get("timeout"):
        notes.append("the working tree was too large to snapshot within the time limit, so that command's effects were not checked.")
        violations.append({"path": "(working tree)", "rule": "integrity-timeout", "action": "recorded"})
    # 0. git itself: if it fails now, only the filesystem checks below can run (REQ-IMH-23)
    refused = st.check_git_config(root, pol) if git_ok else None
    if not git_ok or refused:
        notes.append(f"git {'configuration was refused (' + refused + ')' if refused else 'failed'} after that command "
                     "(git-unavailable), so only the control plane and audit logs were checked.")
        violations.append({"path": "(git)", "rule": "git-unavailable", "action": "recorded"})
        git_ok = False
    elif snap.get("git_dir") and _git_dir_id(root) != snap.get("git_dir"):
        notes.append("the repository's git directory was replaced by that command.")
        violations.append({"path": ".git", "rule": "git-dir-replaced", "action": "recorded"})
    cli_ok = set(snap.get("cli_writes", []))
    # Restoring writes snapshot content back into the control plane, so it is only done
    # when the snapshot is signed; in unsigned mode the change is recorded, never "restored".
    signed = signing.enabled()
    files_now, odd_now = _control_plane_entries(root, pol)
    # 1a. links and non-files at control-plane paths: reported; a new link is removed itself,
    # never anything it points to. One that was already there (a symlinked .claude/skills, say)
    # is not walked, so it is reported too, unless it is already an open violation.
    odd_before = set(snap.get("odd") or [])
    try:
        open_paths = {v.get("path") for v in st.open_violations(root, ctx.change()[0], ctx.branch)}
    except Exception:
        open_paths = set()
    for rel in sorted(odd_before & set(odd_now) - open_paths):
        notes.append(f"{rel} (control plane) is a symlink or not a regular file, so the monitor cannot check what is "
                     "behind it. A human replaces it with a real file or directory.")
        violations.append({"path": rel, "rule": "control-plane-symlink" if os.path.islink(os.path.join(root, rel))
                           else "control-plane-not-a-file", "action": "recorded"})
    for rel in sorted(set(odd_now) - odd_before):
        full = os.path.join(root, rel)
        is_link = os.path.islink(full)
        removed = False
        if is_link and signed:
            try:
                st.remove_file(root, rel)
                removed = True
            except (OSError, ValueError):
                removed = False
        what = "a symlink" if is_link else "not a regular file"
        notes.append(f"{rel} (control plane) is {what}, created by that command"
                     + ("; the link has been removed and nothing it points to was touched." if removed else "; nothing was followed or changed through it."))
        v = {"path": rel, "rule": "control-plane-symlink" if is_link else "control-plane-not-a-file",
             "action": "removed" if removed else "recorded"}
        if removed and not os.path.lexists(full):
            v["resolved"] = "restored"  # verified: the link is gone (REQ-LLA-01)
        violations.append(v)
    # 1. control plane: restore anything that changed, remove anything created
    before = snap.get("cp", {})
    now_files = set(r for r in files_now if not r.startswith(".evidence/audit/"))
    for rel in sorted(set(before) | now_files):
        if rel in cli_ok:
            continue  # written by the evidence CLI itself for this command
        old = before.get(rel)
        cur = _read_cp(root, rel)
        can_restore = signed
        if rel == PERMISSION_FILE and cur is not None and cur != old and (rel not in before or old is not None):
            judged = _local_settings_change(old, cur, pol)
            if judged:
                # kept, and logged by the hook as an audit event, not a violation (B4, REQ-LLA-05)
                if judged[0] == "grant":
                    violations.append({"path": rel, "rule": "permission-grant", "action": "kept", "added": judged[1]})
                else:
                    violations.append({"path": rel, "rule": "config-change", "action": "kept", "summary": judged[1]})
                continue
        if rel in before and old is not None and cur != old:
            verified = False
            if can_restore:
                try:
                    st.write_file(root, rel, base64.b64decode(old))  # never through a planted symlink
                    verified = _read_cp(root, rel) == old  # re-read: the undo is checked, not assumed
                except (OSError, ValueError):
                    can_restore = False
            v = {"path": rel, "rule": "control-plane", "action": "restored" if can_restore else "recorded"}
            if verified:
                v["resolved"] = "restored"
                notes.append(f"{rel} (control plane) was changed by that command and has been restored.")
            elif can_restore:
                notes.append(f"{rel} (control plane) was changed by that command; it was written back from the snapshot, "
                             "but the restore could not be verified (the file differs from the snapshot on re-reading).")
            else:
                notes.append(f"{rel} (control plane) was changed by that command.")
            violations.append(v)
        elif rel not in before and rel in now_files:
            action = "recorded"
            if can_restore:
                try:
                    st.remove_file(root, rel)  # never through a symlinked directory
                    action = "removed"
                except (OSError, ValueError) as e:
                    action = "removal refused"
                    violations.append({"path": rel, "rule": "control-plane-removal-refused", "action": "recorded"})
                    notes.append(f"{rel} could not be removed safely ({e}).")
            notes.append(f"{rel} (control plane) was created by that command" + (" and has been removed." if action == "removed" else "."))
            v = {"path": rel, "rule": "control-plane", "action": action}
            if action == "removed" and not os.path.lexists(os.path.join(root, rel)):
                v["resolved"] = "restored"  # verified: the path is gone (REQ-LLA-01)
            violations.append(v)
    # 1b. git metadata, hidden index flags, ignored entries, user control plane
    before_ex = snap.get("extras") or {}
    if before_ex and git_ok:
        after_ex = _extras(root, pol)
        for k in sorted(set(before_ex) | set(after_ex)):
            b, a = before_ex.get(k), after_ex.get(k)
            how = _extra_change(k, b, a, pol)
            if how == "user-config":
                # a system-managed file the session's user could not write: the human's edit (REQ-LLA-06)
                try:
                    ls = os.lstat(k)
                    owner, mode = ls.st_uid, oct(stat.S_IMODE(ls.st_mode))
                except OSError:
                    owner, mode = None, None
                violations.append({"path": k, "rule": "user-config-changed", "action": "kept",
                                   "old_hash": b.get("h") if isinstance(b, dict) else None,
                                   "new_hash": a.get("h") if isinstance(a, dict) else None,
                                   "owner_uid": owner, "mode": mode})
            elif how:
                notes.append(f"{k} was changed by that command (outside what git status shows).")
                violations.append({"path": k, "rule": "hidden-change", "action": "recorded"})
    # 1c. the .evidence directories themselves: type, mode, owner, identity (REQ-IMH-05).
    # A directory that did not exist before may appear; one that existed may not change.
    now_dirs = _dir_ids(root)
    for rel, was in sorted((snap.get("dirs") or {}).items()):
        if was is not None and now_dirs.get(rel) != was:
            notes.append(f"{rel} (directory) had its type, mode, owner or identity changed by that command.")
            violations.append({"path": rel, "rule": "evidence-dir-changed", "action": "recorded"})
    # 2. audit logs may only grow: the old bytes must still be an exact prefix (REQ-IMH-20)
    before_logs = snap.get("audit", {})
    for name, was in sorted(before_logs.items()):
        rel = f".evidence/audit/{name}"
        if isinstance(was, int):  # a snapshot from before 2.1.0: size only
            ok = _prefix_hash(root, rel, was) is not None
        elif was[0] == "oversize":
            ok = False  # never read, so never checked: refused rather than trusted
        else:
            ok = _prefix_hash(root, rel, was[0]) == was
        if not ok:
            notes.append(f"audit log {name} was truncated, rewritten, replaced or deleted by that command.")
            violations.append({"path": rel, "rule": "audit-tamper", "action": "recorded"})
    # a log created during the call must verify as a log (hash chain, signatures)
    try:
        created = sorted(set(os.listdir(st.audit_dir(root))) - set(before_logs))
    except OSError:
        created = []
    for name in created:
        rel = f".evidence/audit/{name}"
        whole = _prefix_hash(root, rel, None)
        if not name.endswith(".jsonl") or whole is None:
            continue  # links and non-files are reported with the control plane above
        try:
            good = whole[0] != "oversize" and st.audit_verify(os.path.join(root, rel), [])[0]
        except (OSError, ValueError):
            good = False
        if not good:
            notes.append(f"audit log {name} was created by that command and does not verify.")
            violations.append({"path": rel, "rule": "audit-tamper", "action": "recorded"})
    # 3. every other changed file is judged as if it had been an Edit
    after = _dirty(root) if git_ok else None
    if after == "timeout":
        after = None
    elif after is None and git_ok:
        notes.append("git status failed after that command (git-unavailable), so the working tree was not checked.")
        violations.append({"path": "(git)", "rule": "git-unavailable", "action": "recorded"})
    if after is not None:
        prev = snap.get("dirty", {})
        for rel, h in sorted(after.items()):
            if prev.get(rel, "<absent>") == h:
                continue
            if not st.glob_match(rel, pol.get("ungated", [])) and not rel.startswith(".evidence"):
                changed_gated.append(rel)
            if st.glob_match(rel, pol.get("control_plane", [])) or rel in cli_ok:
                continue
            if rel == ".evidence" or rel.startswith(".evidence/"):
                continue  # control-plane files are checked above; profiles and decisions are ungated
            d = judge(rel)
            if d is not None and not d.allow:
                violations.append({"path": rel, "rule": d.rule, "action": "recorded"})
                notes.append(f"{rel} was changed by that command although the gates would have denied it: {d.reason}")
        for rel in sorted(set(prev) - set(after)):
            # A previously dirty file no longer listed. If it still exists it was reverted to
            # HEAD, which is allowed. If it is gone, it was untracked (a deleted tracked file
            # would still be listed), and deleting it is judged like any delete (REQ-IMH-07).
            if os.path.lexists(os.path.join(root, rel)) or rel == ".evidence" or rel.startswith(".evidence/"):
                continue
            if st.glob_match(rel, pol.get("control_plane", [])) or rel in cli_ok:
                continue
            if not st.glob_match(rel, pol.get("ungated", [])):
                changed_gated.append(rel)
            d = judge(rel)
            if d is not None and not d.allow:
                violations.append({"path": rel, "rule": d.rule, "action": "recorded"})
                notes.append(f"{rel} was deleted by that command although the gates would have denied it: {d.reason}")
    return notes, violations, changed_gated
