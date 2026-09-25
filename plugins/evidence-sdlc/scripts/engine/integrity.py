"""Integrity monitor: catches writes the Bash parser could not see.

The PreToolUse parser only understands programs it knows. Any other program
(a compiled binary, awk's system(), make, an npm script) can write files it never
saw. So around every allowed Bash call:

  pre  -- snapshot: content of every existing control-plane file, and a hash of
          every dirty or untracked file in the working tree (git status)
  post -- compare. A control-plane change is reverted from the snapshot. Any other
          changed file is judged as if it had been an Edit; a write the gates would
          have denied becomes a recorded violation, and push/PR stay blocked until a
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
            "audit": _audit_sizes(root), "cli_writes": sorted(cli_writes(ctx)), "root": root, "extras": _extras(root, pol),
            "git_dir": _git_dir_id(root)}
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
    for pat in list(policy.get("user_control_plane", [])) + ["~/.gitconfig", "~/.config/git/config", "~/.claude/CLAUDE.md"]:
        p = os.path.expanduser(pat)
        for f in (glob.glob(p, recursive=True)[:500] if "*" in p else [p]):
            if os.path.isfile(f):
                ex[f] = _hash(f)
    return ex


def _audit_sizes(root):
    d = st.audit_dir(root)
    sizes = {}
    if os.path.isdir(d):
        for n in os.listdir(d):
            try:
                sizes[n] = os.path.getsize(os.path.join(d, n))
            except OSError:
                pass
    return sizes


def check(ctx, judge):
    """Compare against the pre-snapshot. `judge(rel)` returns a deny Decision or None.
    Returns (notes, violations)."""
    import signing
    root, pol = ctx.root, ctx.policy
    tmp, srel = tempfile.gettempdir(), _snap_rel(ctx.session, ctx.payload.get("tool_use_id"))
    git_ok = _is_git(root)
    if not os.path.lexists(os.path.join(tmp, srel)):
        if not git_ok:
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
    # never anything it points to
    for rel in sorted(set(odd_now) - set(snap.get("odd") or [])):
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
        violations.append({"path": rel, "rule": "control-plane-symlink" if is_link else "control-plane-not-a-file",
                           "action": "removed" if removed else "recorded"})
    # 1. control plane: restore anything that changed, remove anything created
    before = snap.get("cp", {})
    now_files = set(r for r in files_now if not r.startswith(".evidence/audit/"))
    for rel in sorted(set(before) | now_files):
        if rel in cli_ok:
            continue  # written by the evidence CLI itself for this command
        old = before.get(rel)
        cur = _read_cp(root, rel)
        can_restore = signed
        if rel in before and old is not None and cur != old:
            if can_restore:
                try:
                    st.write_file(root, rel, base64.b64decode(old))  # never through a planted symlink
                except (OSError, ValueError):
                    can_restore = False
            notes.append(f"{rel} (control plane) was changed by that command" + (" and has been restored." if can_restore else "."))
            violations.append({"path": rel, "rule": "control-plane", "action": "restored" if can_restore else "recorded"})
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
            violations.append({"path": rel, "rule": "control-plane", "action": action})
    # 1b. git metadata, hidden index flags, ignored entries, user control plane
    before_ex = snap.get("extras") or {}
    if before_ex and git_ok:
        after_ex = _extras(root, pol)
        for k in sorted(set(before_ex) | set(after_ex)):
            if before_ex.get(k) != after_ex.get(k):
                notes.append(f"{k} was changed by that command (outside what git status shows).")
                violations.append({"path": k, "rule": "hidden-change", "action": "recorded"})
    # 2. audit logs may only grow, never shrink or be replaced
    for name, size in snap.get("audit", {}).items():
        full = os.path.join(st.audit_dir(root), name)
        if not os.path.isfile(full) or os.path.getsize(full) < size:
            notes.append(f"audit log {name} was truncated or deleted by that command.")
            violations.append({"path": f".evidence/audit/{name}", "rule": "audit-tamper", "action": "recorded"})
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
            # a previously dirty file now clean: reverted to HEAD, which is allowed
            pass
    return notes, violations, changed_gated
