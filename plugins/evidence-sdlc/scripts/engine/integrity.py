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
import hashlib
import json
import os
import re
import subprocess
import tempfile

import state as st

MAX_HASH_BYTES = 8 * 1024 * 1024


def _snap_path(session, tool_use_id):
    d = os.path.join(tempfile.gettempdir(), "evidence-chain-snapshots", re.sub(r"[^A-Za-z0-9_-]", "_", session or "s"))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, re.sub(r"[^A-Za-z0-9_-]", "_", tool_use_id or "last") + ".json")


def _control_plane_files(root, policy):
    found = set()
    for pat in policy.get("control_plane", []):
        if any(ch in pat for ch in "*?["):
            for p in glob.glob(os.path.join(root, pat), recursive=True):
                if os.path.isfile(p):
                    found.add(os.path.relpath(p, root))
        elif os.path.isfile(os.path.join(root, pat)):
            found.add(pat)
    return sorted(found)


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
    for rel in _control_plane_files(root, pol):
        if rel.startswith(".evidence/audit/"):
            continue  # the audit log legitimately grows on every call
        try:
            data = open(os.path.join(root, rel), "rb").read()
            cp[rel] = base64.b64encode(data).decode() if len(data) <= MAX_HASH_BYTES else None
        except OSError:
            pass
    dirty = _dirty(root)
    snap = {"cp": cp, "dirty": dirty if isinstance(dirty, dict) else {}, "timeout": dirty == "timeout",
            "tool_use_id": ctx.payload.get("tool_use_id") or "last", "session": ctx.session, "taken_at": st.now(),
            "audit": _audit_sizes(root), "cli_writes": sorted(cli_writes(ctx)), "root": root, "extras": _extras(root, pol)}
    with open(_snap_path(ctx.session, ctx.payload.get("tool_use_id")), "w") as f:
        json.dump(signing.sign(snap), f)


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
    if not _is_git(root):
        return [], [], []
    p = _snap_path(ctx.session, ctx.payload.get("tool_use_id"))
    if not os.path.isfile(p):
        # pre always snapshots an allowed Bash call in a git repo; a missing snapshot means
        # something removed it, so what the command did cannot be checked.
        return (["the integrity snapshot for that command is missing, so its effects could not be checked."],
                [{"path": "(integrity snapshot)", "rule": "integrity-snapshot-missing", "action": "recorded"}], [])
    try:
        snap = json.load(open(p))
    finally:
        try:
            os.remove(p)
        except OSError:
            pass
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
    cli_ok = set(snap.get("cli_writes", []))
    # 1. control plane: restore anything that changed, remove anything created
    before = snap.get("cp", {})
    now_files = set(r for r in _control_plane_files(root, pol) if not r.startswith(".evidence/audit/"))
    for rel in sorted(set(before) | now_files):
        if rel in cli_ok:
            continue  # written by the evidence CLI itself for this command
        full = os.path.join(root, rel)
        old = before.get(rel)
        cur = None
        if os.path.isfile(full):
            try:
                cur = base64.b64encode(open(full, "rb").read()).decode()
            except OSError:
                cur = None
        # Restoring writes snapshot content back into the control plane, so it is only done
        # when the snapshot is signed; in unsigned mode the change is recorded, never "restored".
        can_restore = signing.enabled()
        if rel in before and old is not None and cur != old:
            if can_restore:
                try:
                    st.write_file(root, rel, base64.b64decode(old))  # never through a planted symlink
                except (OSError, ValueError):
                    can_restore = False
            notes.append(f"{rel} (control plane) was changed by that command" + (" and has been restored." if can_restore else "."))
            violations.append({"path": rel, "rule": "control-plane", "action": "restored" if can_restore else "recorded"})
        elif rel not in before and cur is not None:
            if can_restore:
                os.remove(full)
            notes.append(f"{rel} (control plane) was created by that command" + (" and has been removed." if can_restore else "."))
            violations.append({"path": rel, "rule": "control-plane", "action": "removed" if can_restore else "recorded"})
    # 1b. git metadata, hidden index flags, ignored entries, user control plane
    before_ex = snap.get("extras") or {}
    if before_ex:
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
    after = _dirty(root)
    if after == "timeout":
        after = None
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
