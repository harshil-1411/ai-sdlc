# Baselines and guardrails

Owner: Engineering Director. **Capture the baselines before Phase 1 starts.** After
rollout begins you cannot reconstruct them, and every claim about impact becomes
unfalsifiable.

## Capture now, before anything is installed

| Metric | Source | Baseline | Date |
| --- | --- | --- | --- |
| Lead time: idea to committed requirement | Jira / current process | | |
| Lead time: requirement to merged PR | Jira + git | | |
| Architecture/design decision lead time (a question raised in `spec.md`'s "Areas of concern," or the genuinely-close-decision rule firing in `spec-and-design`, to a recorded decision or an explicit stated non-decision-yet) | `spec.md`/`plan.md` timestamps + git history | | |
| Review time per PR (open to approval) | PR metadata | | |
| Rework cycles per change | PR metadata | | |
| First-pass CI success rate | CI | | |
| Escaped defect rate (found after merge) | Incident/defect tracker | | |
| Change failure rate | Deployment + incident data | | |
| Time to restore | Incident data | | |
| Validation package assembly effort per release | QA/RA time records | | |
| Regression suite execution effort per release | QA time records | | |
| Cost per merged change | Finance + CI | | |

Track architecture/design decision lead time separately from PR review time — the two
diverge independently. Fast code review does not mean fast design approval, and a slow
design-approval step bottlenecks everything downstream of it even when CI is fast.

## Guardrail metrics — watch these harder than the velocity ones

Velocity gains that conceal a rising failure rate are the classic failure of these
programmes. Track together, never separately:

- **Change failure rate.** If it rises while throughput rises, stop and tighten gates.
- **Escaped defects on regulated paths.** Should trend to zero. Any increase is a
  programme-level finding.
- **Review depth.** Review time per change, and the ratio of review time to diff size.
  A sharp fall means approval is becoming theatre.
- **Spot-audit result.** Quarterly, sample approved PRs and have a second reviewer
  assess whether the approval was substantiated. Record the rate. This is the only
  honest check on R4 in the risk assessment, and an inspector will value it precisely
  because it is uncomfortable.
- **Skill trigger rate vs review findings citing the same policy.** Findings should fall
  toward zero once a skill applies the policy while code is written. If they do not,
  the skill is not triggering or has drifted from the official policy.

## Reporting

Monthly to engineering leadership; quarterly to the board with baselines shown
alongside. Present velocity and guardrail metrics on the same page, always.
