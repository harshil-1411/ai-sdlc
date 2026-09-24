"""Advisory template sensor (PostToolUse). Never denies; returns notes or None.

Checks a just-written artifact for the gaps reviewers most often miss:
- spec.md whose "Areas of concern" is missing or still the template placeholder
- a plan whose "Files claimed" is missing or placeholder
- a Tier 2/3 plan whose "Order of work" names no CHECKPOINT step (tier read from the
  plan's own "Risk tier:" line, a sibling spec.md, or the change's state.json)
- a new SKILL.md under plugins/*/skills/* with no eval case yet
"""
import os
import re

import state as st


def _stub(body):
    t = " ".join(body.split())
    return not t or (t.startswith("<") and t.endswith(">"))


def _tier(text, path, root):
    m = re.search(r"^Risk tier:\s*([123])\b", text, re.M)
    if m:
        return int(m.group(1))
    sib = os.path.join(os.path.dirname(path), "spec.md")
    if os.path.isfile(sib):
        m = re.search(r"Risk tier:\s*([123])\b", open(sib, encoding="utf-8", errors="replace").read())
        if m:
            return int(m.group(1))
    m = re.search(r"Tracker:\s*(\S+)", text)
    if m:
        s = st.load_state(root, m.group(1))
        if s and s.get("tier"):
            return int(s["tier"])
    return None


def check(path, root):
    if not path or not os.path.isfile(path):
        return None
    base = os.path.basename(path)
    parent = os.path.basename(os.path.dirname(path))
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    notes = []
    is_plan = base == "plan.md" or (base.endswith(".md") and parent == "plan")
    if base == "spec.md":
        if _stub(st.section(text, "Areas of concern")):
            notes.append(f"{path}'s \"## Areas of concern\" section is missing or still looks like the unfilled template "
                         "placeholder. spec-and-design treats an empty section as suspicious; say so if there really are none.")
    elif is_plan:
        if _stub(st.section(text, "Files claimed")):
            notes.append(f"{path}'s \"## Files claimed\" section is missing or still the template placeholder. Claims are "
                         "enforced: source edits outside them are denied once the plan is approved.")
        tier = _tier(text, path, root)
        if tier and tier >= 2 and "checkpoint" not in st.section(text, "Order of work").lower():
            notes.append(f"{path} is Tier {tier} but its \"## Order of work\" names no CHECKPOINT step "
                         "(codebase-grounded-planning's mid-flight checkpoint for Tier 2/3 work).")
    elif base == "SKILL.md":
        norm = path.replace(os.sep, "/")
        m = re.search(r"(.*/plugins/[^/]+)/skills/([^/]+)/SKILL\.md$", norm) or re.search(r"^(plugins/[^/]+)/skills/([^/]+)/SKILL\.md$", norm)
        if m:
            evals = os.path.join(m.group(1), "evals")
            has = os.path.isdir(evals) and any(d.startswith(m.group(2) + "-") for d in os.listdir(evals))
            if not has:
                notes.append(f"{path} is a skill with no eval case under {evals}/ matching \"{m.group(2)}-*\" "
                             "(definition-of-ready-and-done: eval case added for a new skill).")
    if not notes:
        return None
    return "\n\n".join(n + " Advisory only -- nothing was blocked." for n in notes)
