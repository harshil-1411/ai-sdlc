---
description: Traceability gaps — requirements without passing tests, unapproved or unattributed changes
argument-hint: [--strict]
---
Run `evidence gaps $ARGUMENTS` from the repository root and report the result grouped by
category (NO COVERAGE, SELF-ASSERTED, UNVERIFIED-RESULT, UNTRACED, ORPHANED, DUPLICATE-ID,
MISSING-CHILD). For each blocking gap, name the requirement ID and the one action that
closes it. Do not mark anything verified yourself; a result counts only when a test run
report shows it passed.
