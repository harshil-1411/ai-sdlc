---
type: llm
focus: { source: file, path: '.evidence/test-cases/FIX-221-tenant-isolation.md' }
---

The fixture's `.evidence/context/toolchain.md` records the TestRail template
("Test Case (Steps)") and the required custom fields `custom_tracker_key` and
`custom_automation_status` (Automated / Manual / To Automate). The
testrail-authoring skill says to read those before writing, and requires Tier 3
manual cases to carry attestation content.

PASS only if the authored case file:
- has a title describing the behaviour under test (e.g. "a user cannot open
  a record belonging to another tenant"), not just a feature name;
- has explicit preconditions and one action per step, each with a specific,
  observable expected result (not "no error" / "works correctly");
- sets the profile's tracker-key field to the supplied key —
  `custom_tracker_key` = `FIX-221` (a placeholder like `FIX-<TBD>` is a FAIL,
  since the key was supplied) — and sets `custom_automation_status` to
  `Manual` (or another allowed value), and references REQ-AUTH-09 in the body;
- sets priority from the Tier 3 risk tier; and
- includes attestation fields for the Tier 3 result — tester name, timestamp
  and execution method (screenshot/video reference) — to be filled at
  execution, left blank rather than pre-filled with a result.

FAIL if any of these is missing, if field names are invented instead of the
profile's `custom_tracker_key` / `custom_automation_status`, or if the case
records a result as already passed.
