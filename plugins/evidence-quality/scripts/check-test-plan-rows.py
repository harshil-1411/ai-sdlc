#!/usr/bin/env python3
"""Advisory (SessionStart): requirement IDs in active plans with no named test row.

Checks every plan belonging to an active change under .evidence/changes/, plus any
plan.md / plan/*.md / intent/*/plan.md on disk -- not just the first one found.
Never blocks; prints a SessionStart additionalContext note or nothing.
"""
import glob
import json
import os
import re
import subprocess
import sys

REQ = re.compile(r"REQ-[A-Za-z0-9]+-[0-9]+")
TEST_WORDS = re.compile(r"test|case|spec|eval|manual|review|C[0-9]+", re.I)


def root():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return os.getcwd()


def active_plans(r):
    plans = set()
    for sp in glob.glob(os.path.join(r, ".evidence", "changes", "*", "state.json")):
        try:
            s = json.load(open(sp))
        except (OSError, ValueError):
            continue
        if s.get("stage") == "released":
            continue
        p = s.get("plan") and os.path.join(r, s["plan"])
        if p and os.path.isfile(p):
            plans.add(p)
        k = s.get("key")
        if k and os.path.isfile(os.path.join(r, "plan", f"{k}.md")):
            plans.add(os.path.join(r, "plan", f"{k}.md"))
    if not plans:
        plans.update(p for p in [os.path.join(r, "plan.md")] + glob.glob(os.path.join(r, "plan", "*.md"))
                     + glob.glob(os.path.join(r, "intent", "*", "plan.md")) if os.path.isfile(p))
    return sorted(plans)


def main():
    sys.stdin.read()
    r = root()
    notes = []
    for plan in active_plans(r):
        try:
            text = open(plan, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        missing = []
        for req in sorted(set(REQ.findall(text))):
            if not any(TEST_WORDS.search(line) for line in text.splitlines() if req in line and line.strip().startswith("|")):
                missing.append(req)
        if missing:
            notes.append(f"{os.path.relpath(plan, r)}: {', '.join(missing)}")
    if notes:
        msg = ("Plans with requirement IDs that have no named test row: " + "; ".join(notes)
               + ". A requirement with no test is an incomplete plan; apply the test-strategy skill.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": msg}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
