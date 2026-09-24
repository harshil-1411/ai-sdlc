#!/usr/bin/env python3
"""eval-summary.py <plugin> <results.json|-> [note]: write plugins/<plugin>/evals/SUMMARY.md
from a `claude plugin eval --json` result (with-vs-without ablation). Pass '-' when no
run exists; the summary then says so instead of inventing numbers."""
import json
import os
import sys

root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
plugin, src = sys.argv[1], sys.argv[2]
note = sys.argv[3] if len(sys.argv) > 3 else ""
out = os.path.join(root, "plugins", plugin, "evals", "SUMMARY.md")


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return sum(xs) / len(xs) if xs else None


lines = [f"# {plugin} eval summary", ""]
if src == "-":
    lines += ["No with-vs-without run was recorded for this plugin in the v2 pass.", "", note or "", ""]
    open(out, "w").write("\n".join(lines))
    print(f"wrote {out} (no run)")
    sys.exit(0)

d = json.load(open(src))
cases = d.get("cases", [])
lines += [f"Run: {d.get('startedAt', '?')}, Claude Code {d.get('claudeVersion', '?')}, "
          f"{'PARTIAL (' + str(d.get('partialReason')) + ')' if d.get('partial') else 'complete'}, "
          f"{len(cases)} cases, cost ${d.get('costUsd', 0):.2f}. Scores are the mean over runs; Δ = with − without.",
          "Skill-fired graders are an indicator only (they do not score the baseline arm).", ""]
if note:
    lines += [note, ""]
lines += ["| Case | With | Without | Δ | Skill fired (with) |", "| --- | ---: | ---: | ---: | --- |"]
deltas, fired_n, fire_cases = [], 0, 0
for c in cases:
    w = mean([r.get("score") for r in c.get("arms", {}).get("with", [])])
    wo = mean([r.get("score") for r in c.get("arms", {}).get("without", [])])
    fired = []
    for r in c.get("arms", {}).get("with", []):
        for g in r.get("graders", []):
            if g.get("name") in ("skill-fired", "skill-not-fired"):
                fired.append("yes" if g.get("passed") else "no")
    if fired:
        fire_cases += 1
        fired_n += fired.count("yes") == len(fired)
    dl = (w - wo) if (w is not None and wo is not None) else None
    if dl is not None:
        deltas.append(dl)
    f = lambda x: "—" if x is None else f"{x:.2f}"  # noqa: E731
    lines.append(f"| {c['name']} | {f(w)} | {f(wo)} | {'—' if dl is None else f'{dl:+.2f}'} | {'/'.join(fired) or '—'} |")
pos = sum(1 for x in deltas if x > 0)
neg = sum(1 for x in deltas if x < 0)
lines += ["", f"**Discrimination:** plugin beats baseline on {pos} case(s), ties on {len(deltas) - pos - neg}, "
          f"loses on {neg}. Mean Δ {mean(deltas) if deltas else 0:+.2f}. Skill fired on every run in {fired_n} of "
          f"{fire_cases} trigger-graded case(s).", ""]
open(out, "w").write("\n".join(lines))
print(f"wrote {out}")
