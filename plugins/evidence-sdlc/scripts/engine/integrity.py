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


def _dirty(root):
    out = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"], cwd=root,
                         capture_output=True, timeout=20)
    if out.returncode != 0:
        return None
    files = {}
    parts = out.stdout.decode("utf-8", "replace").split("\0")
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
        files[path] = _hash(full) if os.path.isfile(full) else None
        i += 1
    return files


def snapshot(ctx):
    root, pol = ctx.root, ctx.policy
    if not os.path.isdir(os.path.join(root, ".git")):
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
    snap = {"cp": cp, "dirty": _dirty(root) or {}, "audit": _audit_sizes(root)}
    with open(_snap_path(ctx.session, ctx.payload.get("tool_use_id")), "w") as f:
        json.dump(snap, f)


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
    root, pol = ctx.root, ctx.policy
    p = _snap_path(ctx.session, ctx.payload.get("tool_use_id"))
    if not os.path.isfile(p):
        return [], []
    try:
        snap = json.load(open(p))
    finally:
        try:
            os.remove(p)
        except OSError:
            pass
    notes, violations = [], []
    # 1. control plane: restore anything that changed, remove anything created
    before = snap.get("cp", {})
    now_files = set(r for r in _control_plane_files(root, pol) if not r.startswith(".evidence/audit/"))
    for rel in sorted(set(before) | now_files):
        full = os.path.join(root, rel)
        old = before.get(rel)
        cur = None
        if os.path.isfile(full):
            try:
                cur = base64.b64encode(open(full, "rb").read()).decode()
            except OSError:
                cur = None
        if rel in before and old is not None and cur != old:
            with open(full, "wb") as f:
                f.write(base64.b64decode(old))
            notes.append(f"{rel} (control plane) was changed by that command and has been restored.")
            violations.append({"path": rel, "rule": "control-plane", "action": "restored"})
        elif rel not in before and cur is not None:
            os.remove(full)
            notes.append(f"{rel} (control plane) was created by that command and has been removed.")
            violations.append({"path": rel, "rule": "control-plane", "action": "removed"})
    # 2. audit logs may only grow, never shrink or be replaced
    for name, size in snap.get("audit", {}).items():
        full = os.path.join(st.audit_dir(root), name)
        if not os.path.isfile(full) or os.path.getsize(full) < size:
            notes.append(f"audit log {name} was truncated or deleted by that command.")
            violations.append({"path": f".evidence/audit/{name}", "rule": "audit-tamper", "action": "recorded"})
    # 3. every other changed file is judged as if it had been an Edit
    after = _dirty(root)
    if after is not None:
        prev = snap.get("dirty", {})
        for rel, h in sorted(after.items()):
            if prev.get(rel, "<absent>") == h:
                continue
            if st.glob_match(rel, pol.get("control_plane", [])):
                continue
            d = judge(rel)
            if d is not None and not d.allow:
                violations.append({"path": rel, "rule": d.rule, "action": "recorded"})
                notes.append(f"{rel} was changed by that command although the gates would have denied it: {d.reason}")
        for rel in sorted(set(prev) - set(after)):
            # a previously dirty file now clean: reverted to HEAD, which is allowed
            pass
    return notes, violations
