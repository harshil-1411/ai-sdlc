---
type: llm
---

The organisation's rule ranks characterization candidates by three signals,
not by coverage percentage: (1) the team's **fear list** (files people avoid
touching), (2) **churn** — files changed most in the last year, e.g.
`git log --since=12.months --format= --name-only | sort | uniq -c | sort -rn`,
and (3) **incident / fix signal** — files most often touched by fix commits,
e.g. `git log --since=12.months -i --grep=fix --grep=bug --grep=hotfix --format= --name-only | sort | uniq -c | sort -rn`,
plus incident/postmortem records. Files that appear on two or more lists rank
first, and the ranked list, with its counts, goes back to the team to confirm.

PASS only if the response:
1. Gives a concrete churn command over git history (a `git log` that counts
   changes per file over a recent window — exact flags may differ); AND
2. Gives a concrete command (or clearly specified git query) that counts files
   touched by **fix/bug/hotfix commits** — i.e. filters commits by message
   (`--grep`) or by linked incident — distinct from plain churn; AND
3. Includes asking the team which files they fear/avoid (a fear list); AND
4. Combines the signals — files on more than one list first — and does NOT
   make coverage percentage the primary ranking criterion (coverage may be
   mentioned as secondary context).

FAIL if the fix-commit signal is missing (churn alone, or "hotspots" defined
only by change frequency × complexity), if there is no concrete git command,
if the fear list is missing, or if the ranking is driven primarily by lowest
coverage percentage.
