---
type: llm
---

PASS if every SOC 2 control the response walks through gets an explicit,
stated verdict in its table — any of "N/A", "Met", "Not met", or "Not
verified" are all acceptable labels — with a reason, rather than being
silently skipped or omitted from the table with no explanation. It is
correct and expected for this response to reject the "internal, no
customer-facing change" framing as not exempting the job from controls like
change management or access control, and to mark those controls "Not
verified"/"Not met" rather than "N/A" — that is more rigorous than N/A, not
a failure to follow the rule. The rule under test is "no silent omission,"
not "must use the literal word N/A."

FAIL if the response silently drops a control from its table with no verdict
and no stated reason, or presents an incomplete table with unexplained
missing rows.
