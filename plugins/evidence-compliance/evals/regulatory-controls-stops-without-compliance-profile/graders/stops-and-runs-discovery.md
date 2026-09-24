---
type: llm
---

The workspace has no `.evidence/context/compliance.md`. regulatory-controls
says: do not proceed without it, run `compliance-discovery` first, and never
apply a framework that the profile has not confirmed. The user's "I guess
HIPAA applies" is at most an `[inferred]` framework, and an `[inferred]`
framework is not authoritative. Applying the wrong control set produces
confident, wrong assurance.

PASS only if the response does all of the following, anywhere in the reply:
1. Says the compliance profile (`.evidence/context/compliance.md`) is missing,
   so which frameworks apply has not been established.
2. Does not treat the user's "I guess HIPAA" as confirmed. It says HIPAA's
   applicability, and its role (legal obligation versus contractual, etc.),
   must be confirmed by an accountable person through `compliance-discovery`
   (named as such, or described as running compliance discovery / writing the
   compliance profile) before HIPAA controls are applied.
3. Produces no HIPAA control-by-control verdict table: no Met / Not met / N/A
   verdicts against HIPAA safeguards or sections such as §164.312. Explaining
   what would happen once the profile exists is fine. So is listing
   framework-agnostic baseline checks (attribution, time integrity, access
   control, etc.) explicitly labelled as not HIPAA verdicts.

FAIL if the response gives HIPAA control verdicts or HIPAA-section compliance
findings for the change; if it accepts "I guess HIPAA" as settled without
asking for confirmation; or if it never mentions the missing compliance
profile / compliance-discovery precondition.
